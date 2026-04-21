"""Dry-run service — simula adapter + categorizacao sem gravar em PessoalTransacao.

Fluxo por item/account:
    1. Busca stg com status_processamento in ('PENDENTE', 'DRY_RUN')
    2. Para cada: converte via pluggy_adapter
    3. Simula categorizacao usando regras atuais (sem INSERT)
    4. Detecta duplicatas em PessoalTransacao (por hash fuzzy data+valor+historico)
    5. Retorna preview JSON para UI

Marca stg com status_processamento='DRY_RUN' ao rodar (indica "simulado").
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from app import db
from app.pessoal.models import (
    PessoalCategoria,
    PessoalPluggyAccount,
    PessoalPluggyCategoriaMap,
    PessoalPluggyItem,
    PessoalPluggyTransacaoStg,
    PessoalRegraCategorizacao,
    PessoalTransacao,
)
from app.pessoal.services.parsers.pluggy_adapter import (
    TransacaoPluggyConvertida, stg_to_transacao,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Categorizacao simulada
# ----------------------------------------------------------------------
def _simular_regra_padrao(convertida: TransacaoPluggyConvertida) -> dict[str, Any]:
    """Simula match de PessoalRegraCategorizacao contra historico da convertida.

    Retorna dict com:
        categoria_id, categoria_nome, regra_id, confianca, origem
    """
    historico = (convertida.raw.historico_completo or
                 convertida.raw.historico or "").upper()
    cpf_cnpj = getattr(convertida, "cpf_cnpj", None)

    # Busca regras ativas
    regras = (
        PessoalRegraCategorizacao.query
        .filter_by(ativo=True, tipo_regra="PADRAO")
        .all()
    )

    # Match por CPF/CNPJ primeiro
    if cpf_cnpj:
        for regra in regras:
            if regra.cpf_cnpj_padrao and regra.cpf_cnpj_padrao == cpf_cnpj:
                cat = db.session.get(PessoalCategoria, regra.categoria_id) if regra.categoria_id else None
                return {
                    "categoria_id": regra.categoria_id,
                    "categoria_nome": cat.nome if cat else None,
                    "regra_id": regra.id,
                    "regra_padrao": regra.padrao_historico,
                    "confianca": 100,
                    "origem": "cpf_cnpj",
                }

    # Match substring
    for regra in regras:
        padrao = (regra.padrao_historico or "").upper()
        if not padrao:
            continue
        if padrao in historico:
            # Respeita valor_min/valor_max
            valor = convertida.raw.valor
            if regra.valor_min is not None and valor < Decimal(str(regra.valor_min)):
                continue
            if regra.valor_max is not None and valor > Decimal(str(regra.valor_max)):
                continue
            cat = db.session.get(PessoalCategoria, regra.categoria_id) if regra.categoria_id else None
            return {
                "categoria_id": regra.categoria_id,
                "categoria_nome": cat.nome if cat else None,
                "regra_id": regra.id,
                "regra_padrao": regra.padrao_historico,
                "confianca": float(regra.confianca) if regra.confianca else 100,
                "origem": "padrao",
            }

    return {
        "categoria_id": None,
        "categoria_nome": None,
        "regra_id": None,
        "regra_padrao": None,
        "confianca": None,
        "origem": None,
    }


def _simular_mapa_pluggy(convertida: TransacaoPluggyConvertida) -> dict[str, Any]:
    """Simula categorizacao via PessoalPluggyCategoriaMap (fallback)."""
    if not convertida.categoria_pluggy_id:
        return {"categoria_id": None, "categoria_nome": None, "origem": None}

    mapa = (
        PessoalPluggyCategoriaMap.query
        .filter_by(pluggy_category_id=convertida.categoria_pluggy_id)
        .first()
    )
    if not mapa or not mapa.pessoal_categoria_id:
        return {"categoria_id": None, "categoria_nome": None, "origem": None}

    cat = db.session.get(PessoalCategoria, mapa.pessoal_categoria_id)
    return {
        "categoria_id": mapa.pessoal_categoria_id,
        "categoria_nome": cat.nome if cat else None,
        "origem": "pluggy_cat_map",
        "confianca": float(mapa.confianca) if mapa.confianca else 70,
    }


# ----------------------------------------------------------------------
# Deteccao de duplicata em PessoalTransacao
# ----------------------------------------------------------------------
def _buscar_duplicata_pessoal(
    convertida: TransacaoPluggyConvertida,
    conta_pessoal_id: Optional[int],
) -> Optional[PessoalTransacao]:
    """Tenta achar transacao equivalente em PessoalTransacao (CSV legado).

    Heuristica: mesma data, mesmo valor, mesmo tipo, historico com overlap.
    Se ja existe pluggy_transaction_id no sistema (apos Fase 4), prioriza.
    """
    raw = convertida.raw
    # Fase 1-3: PessoalTransacao nao tem pluggy_transaction_id ainda.
    # Busca apenas por heuristica (data + valor + tipo + conta).
    if not conta_pessoal_id:
        return None

    candidatos = (
        PessoalTransacao.query
        .filter(
            PessoalTransacao.conta_id == conta_pessoal_id,
            PessoalTransacao.data == raw.data,
            PessoalTransacao.valor == raw.valor,
            PessoalTransacao.tipo == raw.tipo,
        )
        .limit(5)
        .all()
    )
    # Match forte se historico normalizado bate
    hist_norm = (raw.historico or "").upper()[:40]
    for cand in candidatos:
        if cand.historico and cand.historico.upper()[:40] == hist_norm:
            return cand
    # Match fraco (apenas data+valor+tipo): retorna o primeiro
    return candidatos[0] if candidatos else None


# ----------------------------------------------------------------------
# Dry-run principal
# ----------------------------------------------------------------------
def dry_run_item(
    pluggy_item_pk: int, limite: Optional[int] = None,
) -> dict[str, Any]:
    """Roda dry-run em todas as stg de um item e retorna preview.

    Args:
        pluggy_item_pk: id local do PessoalPluggyItem
        limite: limitar quantidade analisada (default: tudo)

    Returns:
        dict com stats + lista de transacoes convertidas
    """
    item = db.session.get(PessoalPluggyItem, pluggy_item_pk)
    if item is None:
        raise ValueError(f"Item nao encontrado: {pluggy_item_pk}")

    accounts = PessoalPluggyAccount.query.filter_by(
        pluggy_item_pk=pluggy_item_pk
    ).all()

    total = 0
    categorizadas = 0
    duplicadas = 0
    alertas_count = 0
    preview: list[dict[str, Any]] = []

    for account in accounts:
        conta_pessoal_id = account.conta_pessoal_id
        query = (
            PessoalPluggyTransacaoStg.query
            .filter(PessoalPluggyTransacaoStg.pluggy_account_pk == account.id)
            .filter(PessoalPluggyTransacaoStg.status_processamento.in_(
                ["PENDENTE", "DRY_RUN"]
            ))
            .order_by(PessoalPluggyTransacaoStg.date.desc())
        )
        if limite:
            query = query.limit(limite)

        stgs = query.all()

        for stg in stgs:
            try:
                convertida = stg_to_transacao(stg, account=account)
            except Exception as exc:
                logger.exception(f"Erro convertendo stg id={stg.id}: {exc}")
                preview.append({
                    "stg_id": stg.id,
                    "erro": str(exc),
                })
                continue

            # Categorizacao (prioridade: regra PADRAO; fallback: mapa Pluggy)
            cat_regra = _simular_regra_padrao(convertida)
            cat_final = cat_regra
            if not cat_regra["categoria_id"]:
                cat_mapa = _simular_mapa_pluggy(convertida)
                if cat_mapa["categoria_id"]:
                    cat_final = cat_mapa

            # Duplicata
            duplicata = _buscar_duplicata_pessoal(convertida, conta_pessoal_id)

            if cat_final["categoria_id"]:
                categorizadas += 1
            if duplicata:
                duplicadas += 1
            if convertida.alertas:
                alertas_count += 1
            total += 1

            preview.append({
                "stg_id": stg.id,
                "pluggy_transaction_id": convertida.pluggy_transaction_id,
                "account_id": account.pluggy_account_id,
                "account_type": account.type,
                "data": convertida.raw.data.isoformat(),
                "historico": convertida.raw.historico[:120],
                "descricao": convertida.raw.descricao,
                "valor": float(convertida.raw.valor),
                "tipo": convertida.raw.tipo,
                "saldo": float(convertida.raw.saldo) if convertida.raw.saldo is not None else None,
                "operation_type": convertida.operation_type,
                "merchant_nome": convertida.merchant_nome,
                "cpf_cnpj": getattr(convertida, "cpf_cnpj", None),
                "status_pluggy": convertida.status_pluggy,
                "parcela": (
                    f"{convertida.raw.parcela_atual}/{convertida.raw.parcela_total}"
                    if convertida.raw.parcela_atual else None
                ),
                "categoria_simulada": cat_final,
                "categoria_pluggy": {
                    "id": convertida.categoria_pluggy_id,
                    "descricao": convertida.categoria_pluggy_descricao,
                },
                "duplicata_pessoal_id": duplicata.id if duplicata else None,
                "duplicata_historico": duplicata.historico[:80] if duplicata else None,
                "alertas": convertida.alertas,
            })

            # Marcar stg como DRY_RUN
            if stg.status_processamento == "PENDENTE":
                stg.status_processamento = "DRY_RUN"

    db.session.commit()

    return {
        "item_id": item.pluggy_item_id,
        "accounts": len(accounts),
        "total_analisado": total,
        "categorizadas": categorizadas,
        "sem_categoria": total - categorizadas,
        "duplicadas_em_pessoal": duplicadas,
        "com_alertas": alertas_count,
        "preview": preview,
        "rodado_em": agora_utc_naive().isoformat(),
    }


def marcar_aprovacao(stg_id: int, status: str) -> PessoalPluggyTransacaoStg:
    """Marca stg como APROVADO | REPROVADO | IGNORAR.

    Valida transicao e levanta ValueError se invalida.
    """
    if status not in ("APROVADO", "REPROVADO", "IGNORAR"):
        raise ValueError(f"Status invalido: {status}")
    stg = db.session.get(PessoalPluggyTransacaoStg, stg_id)
    if stg is None:
        raise ValueError(f"STG nao encontrado: {stg_id}")
    if stg.status_processamento == "MIGRADO":
        raise ValueError("STG ja migrada — nao pode ser re-aprovada.")
    stg.status_processamento = status
    db.session.commit()
    return stg


def marcar_aprovacao_em_lote(
    pluggy_item_pk: int, status: str, apenas_dry_run: bool = True,
) -> int:
    """Marca todas as stg de um item em lote."""
    if status not in ("APROVADO", "REPROVADO", "IGNORAR"):
        raise ValueError(f"Status invalido: {status}")

    accounts_ids = [
        a.id for a in
        PessoalPluggyAccount.query.filter_by(pluggy_item_pk=pluggy_item_pk).all()
    ]
    if not accounts_ids:
        return 0

    q = PessoalPluggyTransacaoStg.query.filter(
        PessoalPluggyTransacaoStg.pluggy_account_pk.in_(accounts_ids),
        PessoalPluggyTransacaoStg.status_processamento != "MIGRADO",
    )
    if apenas_dry_run:
        q = q.filter(PessoalPluggyTransacaoStg.status_processamento == "DRY_RUN")

    total = q.update(
        {"status_processamento": status, "atualizado_em": agora_utc_naive()},
        synchronize_session=False,
    )
    db.session.commit()
    return total
