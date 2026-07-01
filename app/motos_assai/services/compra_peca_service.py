"""compra_peca_service — pedido de compra de peca (GARANTIA/COMPRA) (Spec 1 §11).

Numeracao 'PC-AAAA-NNNN' via sequence GLOBAL (nextval atomico, nunca COUNT()/MAX()+1
§13.4; precedente hora_recibo_numero_seq). receber_item alimenta o ledger
(registrar_entrada) e recalcula status do cabecalho. add+flush SEM commit.
"""
from decimal import Decimal

from sqlalchemy import text

from app import db
from app.motos_assai.models import (
    AssaiPeca, AssaiPecaCompra, AssaiPecaCompraItem,
    COMPRA_PECA_TIPOS_VALIDOS,
    COMPRA_PECA_STATUS_ABERTA, COMPRA_PECA_STATUS_PARCIAL,
    COMPRA_PECA_STATUS_RECEBIDA, COMPRA_PECA_STATUS_CANCELADA,
)
from app.motos_assai.services import movimento_service
from app.utils.timezone import agora_brasil_naive


class CompraPecaError(Exception):
    """Erro de dominio de compra_peca_service."""


def _decimal(valor, campo):
    try:
        return Decimal(str(valor))
    except Exception as exc:  # noqa: BLE001
        raise CompraPecaError(f'{campo} invalido: {valor!r}') from exc


def _gerar_numero(ano=None):
    """Proximo 'PC-AAAA-NNNN' via sequence global (nextval — atomico, sem corrida).

    O sufixo NNNN e contador GLOBAL (nao reinicia por ano; o ano e so rotulo do
    prefixo). Unicidade garantida pelo nextval + UNIQUE em assai_peca_compra.numero.
    """
    ano = ano or agora_brasil_naive().year
    seq = int(db.session.execute(
        text("SELECT nextval('assai_peca_compra_numero_seq')")).scalar())
    return f'PC-{ano}-{seq:04d}'


def criar_compra(*, tipo, itens, operador_id, fornecedor='MOTOCHEFE'):
    if tipo not in COMPRA_PECA_TIPOS_VALIDOS:
        raise CompraPecaError(
            f'tipo invalido: {tipo}. Validos: {sorted(COMPRA_PECA_TIPOS_VALIDOS)}')
    if not itens:
        raise CompraPecaError('pelo menos 1 item e obrigatorio')

    compra = AssaiPecaCompra(
        numero=_gerar_numero(), tipo=tipo, status=COMPRA_PECA_STATUS_ABERTA,
        fornecedor=fornecedor, criada_por_id=operador_id,
        criada_em=agora_brasil_naive(),
    )
    db.session.add(compra)
    db.session.flush()

    for it in itens:
        adicionar_item(
            compra_id=compra.id,
            peca_id=it['peca_id'],
            quantidade=it['quantidade'],
            custo_estimado=it.get('custo_estimado'),
            pendencia_id=it.get('pendencia_id'),
        )
    db.session.flush()
    return compra


def adicionar_item(*, compra_id, peca_id, quantidade, custo_estimado=None, pendencia_id=None):
    compra = db.session.get(AssaiPecaCompra, compra_id)
    if not compra:
        raise CompraPecaError(f'compra {compra_id} nao encontrada')
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        raise CompraPecaError('compra cancelada nao aceita novos itens')
    if not db.session.get(AssaiPeca, peca_id):
        raise CompraPecaError(f'peca {peca_id} nao encontrada')
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise CompraPecaError('quantidade deve ser > 0')

    item = AssaiPecaCompraItem(
        compra_id=compra.id,
        peca_id=peca_id,
        quantidade=q,
        quantidade_recebida=Decimal('0'),
        custo_estimado=(_decimal(custo_estimado, 'custo_estimado') if custo_estimado is not None else None),
        pendencia_id=pendencia_id,
        criado_em=agora_brasil_naive(),
    )
    db.session.add(item)
    db.session.flush()
    return item


def receber_item(*, compra_item_id, quantidade, custo_unitario, operador_id):
    item = db.session.get(AssaiPecaCompraItem, compra_item_id)
    if not item:
        raise CompraPecaError(f'item de compra {compra_item_id} nao encontrado')
    compra = item.compra
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        raise CompraPecaError('compra cancelada nao aceita recebimento')
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise CompraPecaError('quantidade deve ser > 0')

    mov = movimento_service.registrar_entrada(
        peca_id=item.peca_id,
        quantidade=q,
        custo_unitario=custo_unitario,
        operador_id=operador_id,
        compra_item_id=item.id,
    )
    item.quantidade_recebida = Decimal(str(item.quantidade_recebida)) + q
    _recalcular_status(compra)
    db.session.flush()
    return mov


def cancelar_compra(*, compra_id, operador_id):
    compra = db.session.get(AssaiPecaCompra, compra_id)
    if not compra:
        raise CompraPecaError(f'compra {compra_id} nao encontrada')
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        return compra  # idempotente
    if compra.status == COMPRA_PECA_STATUS_RECEBIDA:
        raise CompraPecaError('compra ja recebida nao pode ser cancelada')
    compra.status = COMPRA_PECA_STATUS_CANCELADA
    db.session.flush()
    return compra


def _recalcular_status(compra):
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        return
    total = Decimal('0')
    recebido = Decimal('0')
    for it in compra.itens:
        total += Decimal(str(it.quantidade))
        recebido += Decimal(str(it.quantidade_recebida))
    if recebido <= 0:
        compra.status = COMPRA_PECA_STATUS_ABERTA
    elif recebido < total:
        compra.status = COMPRA_PECA_STATUS_PARCIAL
    else:
        compra.status = COMPRA_PECA_STATUS_RECEBIDA
