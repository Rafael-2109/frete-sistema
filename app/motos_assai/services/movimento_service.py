"""movimento_service — ledger de estoque de pecas (Spec 1 §11/§8).

Custeio: media movel ponderada por peca, custo congelado por movimento.
add+flush SEM commit. consumir/canibalizar ficam na Task 8 (este arquivo
cobre entrada/saldo/custo_medio/descartar/ajustar).
"""
from decimal import Decimal

from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiPeca, AssaiEstoqueMovimento,
    MOVIMENTO_ENTRADA, MOVIMENTO_DESCARTE, MOVIMENTO_AJUSTE,
)
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_brasil_naive


class EstoqueError(Exception):
    """Erro de dominio de movimento_service."""


def _decimal(valor, campo):
    try:
        return Decimal(str(valor))
    except Exception as exc:  # noqa: BLE001
        raise EstoqueError(f'{campo} invalido: {valor!r}') from exc


def _exigir_peca(peca_id):
    peca = AssaiPeca.query.get(peca_id)
    if not peca:
        raise EstoqueError(f'peca {peca_id} nao encontrada')
    return peca


def saldo(peca_id):
    total = db.session.query(
        func.coalesce(func.sum(AssaiEstoqueMovimento.delta_almoxarifado), 0)
    ).filter(AssaiEstoqueMovimento.peca_id == peca_id).scalar()
    return Decimal(total)


def custo_medio(peca_id):
    """Media movel ponderada: SUM(delta*custo)/SUM(delta) nas linhas com custo.

    Guarda de divisao por zero (Spec §8): se SUM(delta) <= 0 -> fallback
    custo_referencia -> ultimo custo de ENTRADA -> 0.
    """
    soma_valor, soma_delta = db.session.query(
        func.coalesce(func.sum(
            AssaiEstoqueMovimento.delta_almoxarifado * AssaiEstoqueMovimento.custo_unitario), 0),
        func.coalesce(func.sum(AssaiEstoqueMovimento.delta_almoxarifado), 0),
    ).filter(
        AssaiEstoqueMovimento.peca_id == peca_id,
        AssaiEstoqueMovimento.custo_unitario.isnot(None),
    ).one()

    if soma_delta and Decimal(soma_delta) > 0:
        return (Decimal(soma_valor) / Decimal(soma_delta)).quantize(Decimal('0.0001'))

    peca = AssaiPeca.query.get(peca_id)
    if peca and peca.custo_referencia is not None:
        return Decimal(peca.custo_referencia).quantize(Decimal('0.0001'))

    ultima = (
        AssaiEstoqueMovimento.query
        .filter_by(peca_id=peca_id, tipo=MOVIMENTO_ENTRADA)
        .filter(AssaiEstoqueMovimento.custo_unitario.isnot(None))
        .order_by(AssaiEstoqueMovimento.id.desc())
        .first()
    )
    if ultima and ultima.custo_unitario is not None:
        return Decimal(ultima.custo_unitario).quantize(Decimal('0.0001'))
    return Decimal('0')


def registrar_entrada(*, peca_id, quantidade, custo_unitario, operador_id,
                      compra_item_id=None, recebimento_ref=None):
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise EstoqueError('quantidade deve ser > 0')
    cu = _decimal(custo_unitario, 'custo_unitario')
    if cu < 0:
        raise EstoqueError('custo_unitario nao pode ser negativo')
    _exigir_peca(peca_id)

    dados = {}
    if recebimento_ref:
        dados['recebimento_ref'] = recebimento_ref

    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_ENTRADA,
        quantidade=q,
        delta_almoxarifado=q,
        compra_item_id=compra_item_id,
        custo_unitario=cu,
        custo_total=(q * cu).quantize(Decimal('0.01')),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
        dados_extras=sanitize_for_json(dados),
    )
    db.session.add(mov)
    db.session.flush()
    return mov


def descartar(*, peca_id, quantidade, operador_id, chassi_origem=None, pendencia_id=None):
    """DESCARTE. chassi_origem definido => peca veio de uma moto (nunca foi saldo,
    delta 0); sem chassi_origem => baixa de saldo do almoxarifado (delta -qtd)."""
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise EstoqueError('quantidade deve ser > 0')
    _exigir_peca(peca_id)

    delta = Decimal('0') if chassi_origem else -q
    cu = custo_medio(peca_id)
    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_DESCARTE,
        quantidade=q,
        delta_almoxarifado=delta,
        chassi_origem=(chassi_origem.strip().upper() if chassi_origem else None),
        pendencia_id=pendencia_id,
        custo_unitario=cu,
        custo_total=(q * cu).quantize(Decimal('0.01')),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
    )
    db.session.add(mov)
    db.session.flush()
    return mov


def ajustar(*, peca_id, delta, operador_id, motivo, custo_unitario=None):
    d = _decimal(delta, 'delta')
    if d == 0:
        raise EstoqueError('delta nao pode ser zero')
    if not motivo or len(motivo.strip()) < 3:
        raise EstoqueError('motivo obrigatorio (>=3 chars)')
    _exigir_peca(peca_id)

    cu = _decimal(custo_unitario, 'custo_unitario') if custo_unitario is not None else custo_medio(peca_id)
    mag = abs(d)
    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_AJUSTE,
        quantidade=mag,
        delta_almoxarifado=d,
        custo_unitario=cu,
        custo_total=(mag * cu).quantize(Decimal('0.01')),
        operador_id=operador_id,
        observacao=motivo.strip(),
        ocorrido_em=agora_brasil_naive(),
    )
    db.session.add(mov)
    db.session.flush()
    return mov
