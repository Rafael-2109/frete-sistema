"""Auditoria append-only do recebimento HORA.

Grava TODA acao de conferencia com usuario + valor_antes/depois. Nunca
atualiza ou deleta linhas. Consulta: por recebimento_id, ordem DESC.
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import HoraConferenciaAuditoria


ACOES_VALIDAS = {
    'INICIOU_RECEBIMENTO',
    'DEFINIU_QTD',
    'ALTEROU_QTD',
    'CONFERIU_MOTO',
    'MARCOU_AVARIA',
    'RECONFEREU_MOTO',
    'SUBSTITUIU_CONFERENCIA',
    'FINALIZOU',
    'AJUSTOU_CAMPO',
}


def registrar(
    recebimento_id: int,
    acao: str,
    usuario: Optional[str] = None,
    conferencia_id: Optional[int] = None,
    campo_alterado: Optional[str] = None,
    valor_antes=None,
    valor_depois=None,
    detalhe: Optional[str] = None,
    flush: bool = True,
) -> HoraConferenciaAuditoria:
    """Grava 1 linha de auditoria.

    `flush=True` garante que o id da linha esteja disponivel mas NAO comita;
    a transacao atual deve comitar fora.
    """
    if acao not in ACOES_VALIDAS:
        raise ValueError(f"acao invalida: {acao}. Aceitas: {ACOES_VALIDAS}")

    aud = HoraConferenciaAuditoria(
        recebimento_id=recebimento_id,
        conferencia_id=conferencia_id,
        usuario=usuario,
        acao=acao,
        campo_alterado=campo_alterado,
        valor_antes=_stringify(valor_antes),
        valor_depois=_stringify(valor_depois),
        detalhe=detalhe,
    )
    db.session.add(aud)
    if flush:
        db.session.flush()
    return aud


def _stringify(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, bool):
        return 'true' if v else 'false'
    return str(v)


def listar_por_recebimento(recebimento_id: int, limit: int = 500):
    return (
        HoraConferenciaAuditoria.query
        .filter_by(recebimento_id=recebimento_id)
        .order_by(HoraConferenciaAuditoria.criado_em.desc())
        .limit(limit)
        .all()
    )
