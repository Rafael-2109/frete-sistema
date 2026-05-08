"""Separação por (pedido × loja). Fungível por modelo.

Estados:
- EM_SEPARACAO: criada e aceita novos chassis
- FECHADA: operador clicou Finalizar (saldo zero ou parcial)
- FATURADA: NF Q.P.A. importada e bateu
- CANCELADA: cancelada pelo operador (chassis devolvidos via novo evento DISPONIVEL)
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiMoto, AssaiModelo,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CANCELADA,
    PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,
    EVENTO_DISPONIVEL, EVENTO_SEPARADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


class SeparacaoConflictError(Exception):
    """Race ao reservar chassi (UNIQUE parcial)."""


class SeparacaoValidationError(Exception):
    pass


def get_ou_criar_separacao(pedido_id: int, loja_id: int, operador_id: int) -> AssaiSeparacao:
    """Retorna separação ativa ou cria. UNIQUE parcial garante 1 ativa por (pedido, loja)."""
    sep = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .first()
    )
    if sep:
        return sep

    sep = AssaiSeparacao(
        pedido_id=pedido_id, loja_id=loja_id,
        status=SEPARACAO_STATUS_EM_SEPARACAO,
    )
    db.session.add(sep)
    db.session.flush()
    return sep


def saldo_pendente_por_modelo(pedido_id: int, loja_id: int) -> List[Dict[str, Any]]:
    """Retorna [{modelo_id, codigo, nome, qtd_pedida, qtd_separada, qtd_pendente, valor_unitario}]."""
    rows = (
        db.session.query(
            AssaiPedidoVendaItem.modelo_id,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiPedidoVendaItem.qtd_pedida,
            AssaiPedidoVendaItem.valor_unitario,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(
            AssaiPedidoVendaItem.pedido_id == pedido_id,
            AssaiPedidoVendaItem.loja_id == loja_id,
        )
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # SUM já separado por (modelo) nesta separação ativa
    sep = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        ).first()
    )

    qtd_separada_por_modelo: Dict[int, int] = {}
    if sep:
        sums = (
            db.session.query(
                AssaiSeparacaoItem.modelo_id, func.count(AssaiSeparacaoItem.id)
            )
            .filter(AssaiSeparacaoItem.separacao_id == sep.id)
            .group_by(AssaiSeparacaoItem.modelo_id).all()
        )
        qtd_separada_por_modelo = {mid: int(n) for mid, n in sums}

    result = []
    for r in rows:
        sep_qtd = qtd_separada_por_modelo.get(r.modelo_id, 0)
        result.append({
            'modelo_id': r.modelo_id,
            'codigo': r.codigo,
            'nome': r.nome,
            'qtd_pedida': r.qtd_pedida,
            'qtd_separada': sep_qtd,
            'qtd_pendente': max(0, r.qtd_pedida - sep_qtd),
            'valor_unitario': r.valor_unitario,
        })
    return result


def registrar_chassi(
    pedido_id: int, loja_id: int, chassi: str, registrada_por_id: int,
) -> Dict[str, Any]:
    """Vincula chassi à separação. Validações:

    1. Status da moto = DISPONIVEL
    2. Modelo da moto bate com algum saldo > 0 do pedido para essa loja
    3. UNIQUE chassi via UNIQUE parcial — race retorna 409
    """
    chassi_norm = chassi.strip().upper()

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).with_for_update().first()
    if not moto:
        raise SeparacaoValidationError(f'Chassi {chassi_norm} não cadastrado')

    status = status_efetivo(chassi_norm)
    if status != EVENTO_DISPONIVEL:
        raise SeparacaoValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado DISPONIVEL'
        )

    # Saldo: encontrar item do pedido com modelo bate
    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    saldo_modelo = next(
        (s for s in saldos if s['modelo_id'] == moto.modelo_id and s['qtd_pendente'] > 0),
        None,
    )
    if not saldo_modelo:
        raise SeparacaoValidationError(
            f'Modelo {moto.modelo.codigo} sem saldo pendente para esta loja '
            '(ou modelo não pertence ao pedido)'
        )

    sep = get_ou_criar_separacao(pedido_id, loja_id, registrada_por_id)

    try:
        item = AssaiSeparacaoItem(
            separacao_id=sep.id,
            chassi=chassi_norm,
            modelo_id=moto.modelo_id,
            valor_unitario_qpa=Decimal(str(saldo_modelo['valor_unitario'])),
            registrada_por_id=registrada_por_id,
        )
        db.session.add(item)
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise SeparacaoConflictError(
            f'Chassi {chassi_norm} já em outra separação ativa'
        )

    emitir_evento(
        chassi_norm, EVENTO_SEPARADA,
        operador_id=registrada_por_id,
        dados_extras={
            'separacao_id': sep.id, 'pedido_id': pedido_id, 'loja_id': loja_id,
        },
    )

    # Pedido -> SEPARANDO
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if pedido and pedido.status == PEDIDO_STATUS_EM_PRODUCAO:
        pedido.status = PEDIDO_STATUS_SEPARANDO

    db.session.commit()
    return {
        'separacao_id': sep.id,
        'item_id': item.id,
        'chassi': chassi_norm,
        'modelo_codigo': moto.modelo.codigo,
        'cor': moto.cor,
    }


def desfazer_chassi(separacao_item_id: int, operador_id: int) -> Dict[str, Any]:
    """Remove chassi da separação ativa. Emite DISPONIVEL para o chassi voltar."""
    item = AssaiSeparacaoItem.query.get_or_404(separacao_item_id)
    sep = AssaiSeparacao.query.get(item.separacao_id)
    if sep and sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(
            f'Separação {sep.id} está {sep.status}, não permite desfazer'
        )

    chassi = item.chassi
    db.session.delete(item)
    emitir_evento(
        chassi, EVENTO_DISPONIVEL,
        operador_id=operador_id,
        observacao='desfeito da separação',
        dados_extras={'separacao_id': sep.id if sep else None},
    )
    db.session.commit()
    return {'chassi': chassi}


def finalizar_separacao(separacao_id: int, operador_id: int) -> AssaiSeparacao:
    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(f'Status atual: {sep.status}')

    from app.utils.timezone import agora_brasil_naive
    sep.status = SEPARACAO_STATUS_FECHADA
    sep.fechada_em = agora_brasil_naive()
    sep.fechada_por_id = operador_id
    db.session.commit()
    return sep


def cancelar_separacao(separacao_id: int, motivo: str, operador_id: int) -> AssaiSeparacao:
    """Cancela. Para cada item: emite DISPONIVEL para devolver chassi ao estoque."""
    if not motivo or len(motivo.strip()) < 3:
        raise SeparacaoValidationError('Motivo obrigatório (≥3 chars)')

    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status == SEPARACAO_STATUS_CANCELADA:
        raise SeparacaoValidationError('Já cancelada')

    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()
    for it in items:
        emitir_evento(
            it.chassi, EVENTO_DISPONIVEL,
            operador_id=operador_id,
            observacao='separacao_cancelada',
            dados_extras={'separacao_id': sep.id, 'motivo': motivo.strip()},
        )

    sep.status = SEPARACAO_STATUS_CANCELADA
    sep.motivo_cancelamento = motivo.strip()
    db.session.commit()
    return sep
