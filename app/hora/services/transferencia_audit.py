"""Auditoria append-only de transferencias entre filiais HORA.

Padrao identico ao recebimento_audit: nunca UPDATE/DELETE, registra em
hora_transferencia_auditoria.
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import HoraTransferenciaAuditoria


ACOES_VALIDAS = {
    'EMITIU', 'CONFIRMOU_ITEM', 'FINALIZOU', 'CANCELOU',
    'ADICIONOU_FOTO', 'EDITOU_OBSERVACAO',
}


def registrar_auditoria(
    transferencia_id: int,
    usuario: str,
    acao: str,
    *,
    item_id: Optional[int] = None,
    campo_alterado: Optional[str] = None,
    valor_antes: Optional[str] = None,
    valor_depois: Optional[str] = None,
    detalhe: Optional[str] = None,
) -> HoraTransferenciaAuditoria:
    if acao not in ACOES_VALIDAS:
        raise ValueError(f"acao invalida: {acao}. Aceitos: {ACOES_VALIDAS}")
    audit = HoraTransferenciaAuditoria(
        transferencia_id=transferencia_id,
        item_id=item_id,
        usuario=usuario,
        acao=acao,
        campo_alterado=campo_alterado,
        valor_antes=valor_antes,
        valor_depois=valor_depois,
        detalhe=detalhe,
    )
    db.session.add(audit)
    db.session.flush()
    return audit
