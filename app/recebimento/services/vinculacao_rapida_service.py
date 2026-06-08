"""Núcleo determinístico de vinculação NF×PO por número de NF (sem LLM).

FASE 3 do plano docs/superpowers/plans/2026-06-08-fastpath-vinculacao-nf-po.md.

Reusa o pipeline existente do recebimento (validar_dfe + consolidar_pos +
reverter_consolidacao). NUNCA levanta — encapsula falha em {ok: False, anomalia},
para o caller (fast-path do agente) cair no LLM/gestor-recebimento (N2).
"""
from __future__ import annotations

import logging

from app import db
from app.recebimento.models import ValidacaoNfPoDfe, MatchNfPoItem
from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService
from app.recebimento.services.odoo_po_service import OdooPoService

logger = logging.getLogger(__name__)


def _norm_po(s) -> str:
    return str(s or "").strip().upper()


def _buscar_validacoes_por_nf(numero_nf: str):
    return (ValidacaoNfPoDfe.query
            .filter_by(numero_nf=str(numero_nf).strip())
            .order_by(ValidacaoNfPoDfe.atualizado_em.desc().nullslast())
            .all())


def montar_pos_para_consolidar(validacao_id: int) -> list[dict]:
    """Agrupa MatchNfPoItem('match') por PO e ordena por valor desc.

    Extraído de validacao_nf_po_routes.consolidar_pos (DRY) — a rota web e o
    fast-path determinístico usam a MESMA montagem.
    """
    matches = (db.session.query(MatchNfPoItem)
               .filter_by(validacao_id=validacao_id, status_match="match").all())
    pos_dict: dict = {}
    for m in matches:
        if not m.odoo_po_id:
            continue
        d = pos_dict.setdefault(m.odoo_po_id, {
            "po_id": m.odoo_po_id, "po_name": m.odoo_po_name,
            "linhas": [], "valor_total": 0,
        })
        d["linhas"].append({"po_line_id": m.odoo_po_line_id, "qtd_nf": m.qtd_nf,
                            "qtd_po": m.qtd_po, "preco": m.preco_nf})
        d["valor_total"] += (m.qtd_nf or 0) * (m.preco_nf or 0)
    return sorted(pos_dict.values(), key=lambda x: x["valor_total"], reverse=True)


def executar_vinculacao_por_nf(nf: str, po_esperado: str | None,
                               acao: str, usuario: str | None) -> dict:
    """Roteia (des)vinculação NF×PO para as funções existentes do recebimento.

    Retorna SEMPRE um dict com chaves: ok, acao, nf, po, status, resumo, anomalia.
    Caminho feliz só efetiva com status='aprovado' (vincular) + PO confirmado;
    qualquer anomalia => ok=False (caller decide N1/N2). NUNCA levanta.
    """
    base = {"ok": False, "acao": acao, "nf": str(nf), "po": po_esperado,
            "status": None, "resumo": None, "anomalia": None}
    try:
        vals = _buscar_validacoes_por_nf(nf)
        if not vals:
            base["anomalia"] = {"tipo": "nf_nao_encontrada",
                                "detalhe": f"NF {nf} não está na carteira de validação.",
                                "validacao_id": None}
            return base
        if len(vals) > 1 and not po_esperado:
            base["anomalia"] = {"tipo": "nf_ambigua",
                                "detalhe": f"{len(vals)} NFs com número {nf}; informe o fornecedor.",
                                "validacao_id": None}
            return base
        val = vals[0]
        base["status"] = val.status

        if acao == "desvincular":
            res = OdooPoService().reverter_consolidacao(validacao_id=val.id, usuario=usuario)
            if res.get("sucesso"):
                base.update(ok=True, status="revertido", resumo=res)
                return base
            base["anomalia"] = {"tipo": "erro_execucao",
                                "detalhe": res.get("erro", "reversão falhou"),
                                "validacao_id": val.id}
            return base

        # acao == "vincular": rodar match determinístico (já existente)
        res = ValidacaoNfPoService().validar_dfe(val.odoo_dfe_id)
        status = res.get("status")
        base["status"] = status
        if status == "finalizado_odoo":
            base.update(ok=True, resumo=res)
            return base
        if status != "aprovado":
            base["anomalia"] = {"tipo": "status_nao_aprovado", "detalhe": status,
                                "validacao_id": val.id, "validacao": res}
            return base

        pos = montar_pos_para_consolidar(val.id)
        po_names = {_norm_po(p["po_name"]) for p in pos}
        if po_esperado and _norm_po(po_esperado) not in po_names:
            base["anomalia"] = {"tipo": "po_diverge",
                                "detalhe": f"NF casou com {sorted(po_names)}, não com {po_esperado}.",
                                "validacao_id": val.id}
            return base

        cons = OdooPoService().consolidar_pos(
            validacao_id=val.id, pos_para_consolidar=pos,
            usuario=usuario, quantidades_customizadas=None)
        if cons.get("sucesso"):
            base.update(ok=True, status="consolidado", resumo=cons)
            return base
        base["anomalia"] = {"tipo": "erro_execucao",
                            "detalhe": cons.get("erro", "consolidação falhou"),
                            "validacao_id": val.id}
        return base
    except Exception as e:
        logger.warning(f"[VINC-RAPIDA] falha (-> N2) nf={nf} po={po_esperado}: {e}", exc_info=True)
        base["anomalia"] = {"tipo": "erro_execucao", "detalhe": str(e), "validacao_id": None}
        return base
