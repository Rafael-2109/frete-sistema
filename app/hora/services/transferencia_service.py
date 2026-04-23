"""Service de transferencia de motos entre filiais HORA.

Fluxo (2 eventos em hora_moto_evento):
  1. Loja origem emite → evento EM_TRANSITO (loja_id=destino)
  2. Loja destino confirma → evento TRANSFERIDA (loja_id=destino)
Cancelamento (origem enquanto EM_TRANSITO):
  → evento CANCELADA (loja_id=origem), apenas para itens ainda nao confirmados.
"""
from __future__ import annotations

from typing import Iterable, Optional

from app import db
from app.hora.models import (
    HoraMoto, HoraMotoEvento,
    HoraTransferencia, HoraTransferenciaItem, HoraLoja,
)
from app.hora.services.moto_service import registrar_evento
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.hora.services.transferencia_audit import registrar_auditoria
from app.utils.timezone import agora_utc_naive


def _ultimo_evento(chassi: str) -> Optional[HoraMotoEvento]:
    return (HoraMotoEvento.query
            .filter_by(numero_chassi=chassi)
            .order_by(HoraMotoEvento.timestamp.desc())
            .first())


def _chassi_esta_em_transferencia_ativa(chassi: str) -> bool:
    q = (
        db.session.query(HoraTransferenciaItem.id)
        .join(HoraTransferencia,
              HoraTransferencia.id == HoraTransferenciaItem.transferencia_id)
        .filter(
            HoraTransferenciaItem.numero_chassi == chassi,
            HoraTransferencia.status == 'EM_TRANSITO',
        )
    )
    return bool(db.session.query(q.exists()).scalar())


def criar_transferencia(
    loja_origem_id: int,
    loja_destino_id: int,
    chassis: Iterable[str],
    usuario: str,
    observacoes: Optional[str] = None,
) -> HoraTransferencia:
    """Emite transferencia (status=EM_TRANSITO) com N chassis.

    Raises:
        ValueError em qualquer validacao falha.
    """
    chassis_list = [c.strip().upper() for c in chassis if c and c.strip()]
    if not chassis_list:
        raise ValueError("Transferencia requer pelo menos 1 chassi")
    if loja_origem_id == loja_destino_id:
        raise ValueError("loja origem e destino devem ser diferentes")

    # Validar cada chassi
    for chassi in chassis_list:
        moto = HoraMoto.query.get(chassi)
        if not moto:
            raise ValueError(f"chassi inexistente: {chassi}")
        # Primeiro: checa se ja esta em uma transferencia ativa
        if _chassi_esta_em_transferencia_ativa(chassi):
            raise ValueError(f"chassi {chassi} ja esta em transito")
        ev = _ultimo_evento(chassi)
        if ev is None or ev.tipo not in EVENTOS_EM_ESTOQUE:
            tipo = ev.tipo if ev else None
            raise ValueError(
                f"chassi {chassi} nao esta em estoque (ultimo evento: {tipo})"
            )
        if ev.loja_id != loja_origem_id:
            raise ValueError(
                f"chassi {chassi} nao esta na loja origem "
                f"(esta em loja_id={ev.loja_id})"
            )

    transferencia = HoraTransferencia(
        loja_origem_id=loja_origem_id,
        loja_destino_id=loja_destino_id,
        status='EM_TRANSITO',
        emitida_em=agora_utc_naive(),
        emitida_por=usuario,
        observacoes=observacoes,
    )
    db.session.add(transferencia)
    db.session.flush()

    origem = HoraLoja.query.get(loja_origem_id)
    destino = HoraLoja.query.get(loja_destino_id)
    origem_lbl = getattr(origem, 'rotulo_display', None) or f'id={loja_origem_id}'
    destino_lbl = getattr(destino, 'rotulo_display', None) or f'id={loja_destino_id}'

    for chassi in chassis_list:
        item = HoraTransferenciaItem(
            transferencia_id=transferencia.id,
            numero_chassi=chassi,
        )
        db.session.add(item)
        db.session.flush()

        registrar_evento(
            numero_chassi=chassi,
            tipo='EM_TRANSITO',
            origem_tabela='hora_transferencia_item',
            origem_id=item.id,
            loja_id=loja_destino_id,
            operador=usuario,
            detalhe=f"Transf #{transferencia.id}: de {origem_lbl} para {destino_lbl}",
        )

    registrar_auditoria(
        transferencia_id=transferencia.id,
        usuario=usuario,
        acao='EMITIU',
        detalhe=(
            f"emitiu transferencia de {origem_lbl} para {destino_lbl} "
            f"com {len(chassis_list)} chassi(s)"
        ),
    )
    db.session.flush()
    return transferencia


def confirmar_item_destino(
    transferencia_id: int,
    numero_chassi: str,
    usuario: str,
    qr_code_lido: bool = False,
    foto_s3_key: Optional[str] = None,
    observacao: Optional[str] = None,
) -> HoraTransferenciaItem:
    """Confirma chegada de 1 chassi no destino. Idempotente se ja confirmado.

    Usa SELECT FOR UPDATE no header para bloquear concorrencia com cancelar.
    """
    chassi = numero_chassi.strip().upper()
    transferencia = (
        db.session.query(HoraTransferencia)
        .filter(HoraTransferencia.id == transferencia_id)
        .with_for_update()
        .first()
    )
    if not transferencia:
        raise ValueError(f"transferencia {transferencia_id} inexistente")
    if transferencia.status != 'EM_TRANSITO':
        raise ValueError(
            f"transferencia {transferencia_id} nao esta em transito "
            f"(status={transferencia.status})"
        )
    item = (
        HoraTransferenciaItem.query
        .filter_by(transferencia_id=transferencia_id, numero_chassi=chassi)
        .first()
    )
    if not item:
        raise ValueError(
            f"chassi {chassi} nao pertence a transferencia {transferencia_id}"
        )
    if item.conferido_destino_em is not None:
        return item  # idempotente

    item.conferido_destino_em = agora_utc_naive()
    item.conferido_destino_por = usuario
    item.qr_code_lido = bool(qr_code_lido)
    if foto_s3_key:
        item.foto_s3_key = foto_s3_key
    if observacao:
        item.observacao_item = observacao

    registrar_evento(
        numero_chassi=chassi,
        tipo='TRANSFERIDA',
        origem_tabela='hora_transferencia_item',
        origem_id=item.id,
        loja_id=transferencia.loja_destino_id,
        operador=usuario,
        detalhe=f"Chegou via Transf #{transferencia.id}",
    )

    registrar_auditoria(
        transferencia_id=transferencia_id,
        usuario=usuario,
        acao='CONFIRMOU_ITEM',
        item_id=item.id,
        detalhe=(
            f"confirmou chassi {chassi} (qr_code_lido={qr_code_lido}, "
            f"foto={'sim' if foto_s3_key else 'nao'})"
        ),
    )
    db.session.flush()
    return item


def finalizar_se_tudo_confirmado(transferencia_id: int) -> bool:
    """Muda status → CONFIRMADA se todos itens confirmados. Retorna True se finalizou.

    Usa SELECT FOR UPDATE para evitar race com cancelamento concorrente.
    """
    transferencia = (
        db.session.query(HoraTransferencia)
        .filter(HoraTransferencia.id == transferencia_id)
        .with_for_update()
        .first()
    )
    if not transferencia or transferencia.status != 'EM_TRANSITO':
        return False
    pendentes = [i for i in transferencia.itens if i.conferido_destino_em is None]
    if pendentes:
        return False

    ultimo_confirmador = (
        max(transferencia.itens, key=lambda i: i.conferido_destino_em)
        .conferido_destino_por
    )

    transferencia.status = 'CONFIRMADA'
    transferencia.confirmada_em = agora_utc_naive()
    transferencia.confirmada_por = ultimo_confirmador

    registrar_auditoria(
        transferencia_id=transferencia_id,
        usuario=ultimo_confirmador,
        acao='FINALIZOU',
        detalhe=f"todos os {len(transferencia.itens)} chassi(s) confirmados",
    )
    db.session.flush()
    return True


def cancelar_transferencia(
    transferencia_id: int,
    motivo: str,
    usuario: str,
) -> HoraTransferencia:
    """Cancela transferencia em transito. Emite CANCELADA para itens nao confirmados.

    Usa SELECT FOR UPDATE no header para bloquear concorrencia com confirmar.
    """
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError("motivo de cancelamento obrigatorio (min 3 chars)")

    transferencia = (
        db.session.query(HoraTransferencia)
        .filter(HoraTransferencia.id == transferencia_id)
        .with_for_update()
        .first()
    )
    if not transferencia:
        raise ValueError(f"transferencia {transferencia_id} inexistente")
    if transferencia.status != 'EM_TRANSITO':
        raise ValueError(
            f"nao pode cancelar transferencia com status={transferencia.status}"
        )

    transferencia.status = 'CANCELADA'
    transferencia.cancelada_em = agora_utc_naive()
    transferencia.cancelada_por = usuario
    transferencia.motivo_cancelamento = motivo_limpo[:255]

    for item in transferencia.itens:
        if item.conferido_destino_em is not None:
            continue  # ja confirmado — nao reverte
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='CANCELADA',
            origem_tabela='hora_transferencia',
            origem_id=transferencia.id,
            loja_id=transferencia.loja_origem_id,
            operador=usuario,
            detalhe=f"Transf #{transferencia.id} cancelada: {motivo_limpo[:180]}",
        )

    registrar_auditoria(
        transferencia_id=transferencia.id,
        usuario=usuario,
        acao='CANCELOU',
        detalhe=f"motivo: {motivo_limpo}",
    )
    db.session.flush()
    return transferencia
