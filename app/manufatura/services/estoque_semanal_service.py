"""
Relatório Semanal de Estoque — orquestração (queries + Excel + e-mail).

Gera UM .xlsx (Insumos / Embalagens / Produto_Acabado [/ Outros]) comparando o
saldo da segunda anterior com o da segunda atual, com entradas, consumos e
"outros ajustes". Entregue por e-mail toda segunda às 8h (job no scheduler,
atrás da flag ESTOQUE_SEMANAL_EMAIL_ENABLED). Regras puras em
`estoque_semanal_calc.py`.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import date
from typing import Any, Dict, List, Tuple

import pandas as pd
from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.producao.models import CadastroPalletizacao
from app.notificacoes.email_sender import EmailSender
from app.manufatura.services.estoque_semanal_calc import (
    semanas_referencia, montar_abas,
)

logger = logging.getLogger(__name__)

ARQUIVO = "estoque_semanal.xlsx"

# Rótulos das colunas de movimento por aba (sentido do grupo).
_ROTULOS = {
    "Insumos": ("Entradas (compras)", "Consumos (produção)"),
    "Embalagens": ("Entradas (compras)", "Consumos (produção)"),
    "Produto_Acabado": ("Entradas (produção)", "Saídas (vendas)"),
    "Outros": ("Entradas", "Consumos/Saídas"),
}


# ---------------------------------------------------------------- queries --
def _saldo_ate(data_limite: date) -> Dict[str, float]:
    rows = (
        db.session.query(
            MovimentacaoEstoque.cod_produto,
            func.sum(MovimentacaoEstoque.qtd_movimentacao),
        )
        .filter(
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.data_movimentacao < data_limite,
        )
        .group_by(MovimentacaoEstoque.cod_produto)
        .all()
    )
    return {str(c): float(s or 0) for c, s in rows}


def _movimentos_periodo(ini: date, fim: date) -> List[Tuple[str, str, str, float]]:
    rows = (
        db.session.query(
            MovimentacaoEstoque.cod_produto,
            MovimentacaoEstoque.tipo_movimentacao,
            MovimentacaoEstoque.local_movimentacao,
            func.sum(MovimentacaoEstoque.qtd_movimentacao),
        )
        .filter(
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.data_movimentacao >= ini,
            MovimentacaoEstoque.data_movimentacao < fim,
        )
        .group_by(
            MovimentacaoEstoque.cod_produto,
            MovimentacaoEstoque.tipo_movimentacao,
            MovimentacaoEstoque.local_movimentacao,
        )
        .all()
    )
    return [(str(c), t, l, float(q or 0)) for c, t, l, q in rows]


def _cadastro_map() -> Dict[str, Dict[str, str]]:
    rows = CadastroPalletizacao.query.filter_by(ativo=True).all()
    return {
        str(r.cod_produto): {
            "nome_produto": r.nome_produto or "",
            "categoria": r.categoria_produto or "",
            "tipo_materia_prima": r.tipo_materia_prima or "",
            "embalagem": r.tipo_embalagem or "",
        }
        for r in rows
    }


def _mapa_unificacao() -> Dict[str, str]:
    rows = (
        db.session.query(
            UnificacaoCodigos.codigo_origem, UnificacaoCodigos.codigo_destino
        )
        .filter(UnificacaoCodigos.ativo.is_(True))
        .all()
    )
    return {str(o): str(d) for o, d in rows}


# ---------------------------------------------------------- composição -----
def montar_relatorio_semanal() -> Tuple[Dict[str, List[Dict[str, Any]]], date, date]:
    seg_ant, seg_atual = semanas_referencia(agora_utc_naive().date())
    estoque0 = _saldo_ate(seg_ant)
    estoque_hoje = _saldo_ate(seg_atual)
    movimentos = _movimentos_periodo(seg_ant, seg_atual)
    abas = montar_abas(estoque0, estoque_hoje, movimentos,
                       _cadastro_map(), _mapa_unificacao())
    return abas, seg_ant, seg_atual


# ------------------------------------------------------------------ Excel --
_COLS_ORDEM = [
    "cod_produto", "nome_produto", "categoria",
    "estoque_seg_anterior", "entradas", "consumos",
    "outros_ajustes", "estoque_seg_atual",
]


def gerar_planilha_bytes(abas: Dict[str, List[Dict[str, Any]]],
                         seg_ant: date, seg_atual: date) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        escreveu = False
        for aba in ("Insumos", "Embalagens", "Produto_Acabado", "Outros"):
            linhas = abas.get(aba) or []
            if aba == "Outros" and not linhas:
                continue
            rot_ent, rot_con = _ROTULOS[aba]
            colunas = {
                "cod_produto": "Cód", "nome_produto": "Produto", "categoria": "Categoria",
                "estoque_seg_anterior": f"Estoque seg {seg_ant.strftime('%d/%m')}",
                "entradas": rot_ent, "consumos": rot_con,
                "outros_ajustes": "Outros ajustes",
                "estoque_seg_atual": f"Estoque seg {seg_atual.strftime('%d/%m')}",
            }
            df = pd.DataFrame(linhas, columns=_COLS_ORDEM).rename(columns=colunas)
            df.to_excel(writer, sheet_name=aba[:31], index=False)
            escreveu = True
        if not escreveu:
            pd.DataFrame([]).to_excel(writer, sheet_name="Vazio", index=False)
    return buffer.getvalue()


# ------------------------------------------------------------------ e-mail --
def enviar_estoque_semanal_email(dry_run: bool = False) -> dict:
    abas, seg_ant, seg_atual = montar_relatorio_semanal()
    conteudo = gerar_planilha_bytes(abas, seg_ant, seg_atual)
    periodo = f"{seg_ant.strftime('%d/%m')} a {seg_atual.strftime('%d/%m/%Y')}"
    total_linhas = sum(len(v) for v in abas.values())
    resultado = {"ok": True, "periodo": periodo, "linhas": total_linhas,
                 "dry_run": dry_run, "arquivo": ARQUIVO}

    if dry_run:
        resultado["motivo"] = "dry_run"
        return resultado

    destinos = [e.strip() for e in os.getenv("ESTOQUE_SEMANAL_EMAIL_TO", "").split(",") if e.strip()]
    if not destinos:
        logger.warning("[ESTOQUE-SEMANAL] sem destinatário (ESTOQUE_SEMANAL_EMAIL_TO vazio)")
        return {"ok": False, "motivo": "sem_destinatario", "periodo": periodo}

    sender = EmailSender()
    assunto = f"Relatório semanal de estoque — semana de {periodo}"
    corpo = (
        f"<p>Segue em anexo o relatório semanal de estoque "
        f"(comparativo {periodo}).</p>"
        f"<p>Abas: Insumos, Embalagens e Produto Acabado. "
        f"Colunas: estoque na segunda anterior, entradas, consumos/saídas, "
        f"outros ajustes e estoque na segunda atual.</p>"
    )
    res = sender.send(
        to=destinos[0], subject=assunto, body_html=corpo,
        cc=destinos[1:] or None,
        attachments=[(ARQUIVO, conteudo)],
    )
    resultado["ok"] = bool(res.get("success"))
    resultado["motivo"] = "enviado" if res.get("success") else "falha_envio"
    resultado["email"] = res
    return resultado
