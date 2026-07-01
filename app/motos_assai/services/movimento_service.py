"""movimento_service — ledger de estoque de pecas (Spec 1 §11/§8).

Custeio: media movel ponderada por peca, custo congelado por movimento.
add+flush SEM commit. consumir/canibalizar ficam na Task 8 (este arquivo
cobre entrada/saldo/custo_medio/descartar/ajustar).
"""
from decimal import Decimal

from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiPeca, AssaiEstoqueMovimento, AssaiPendencia,
    MOVIMENTO_ENTRADA, MOVIMENTO_DESCARTE, MOVIMENTO_AJUSTE,
    EVENTOS_FORA_ESTOQUE,
)
from app.motos_assai.services.moto_evento_service import status_efetivo
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
    peca = db.session.get(AssaiPeca, peca_id)
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

    peca = db.session.get(AssaiPeca, peca_id)
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


def consumir(
    *, peca_id, quantidade, pendencia_id, chassi_destino, operador_id,
    receita_unitaria=None,
):
    """Baixa de saldo (CONSUMO, delta -qtd) atendendo uma pendencia (USAR_ESTOQUE).

    Congela custo_unitario = custo_medio(peca) na linha (auditavel). Se a ficha
    atendida e categoria=VENDA e receita_unitaria foi informada, grava receita.
    add + flush, SEM commit (caller commita).
    """
    from app.motos_assai.models import (
        AssaiPendencia, AssaiEstoqueMovimento, MOVIMENTO_CONSUMO,
        PENDENCIA_CATEGORIA_VENDA,
    )

    qtd = Decimal(str(quantidade))
    if qtd <= 0:
        raise EstoqueError('Quantidade deve ser positiva.')
    _exigir_peca(peca_id)
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise EstoqueError(f'Pendencia {pendencia_id} nao encontrada.')

    custo = custo_medio(peca_id)
    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_CONSUMO,
        quantidade=qtd,
        delta_almoxarifado=-qtd,
        chassi_destino=(chassi_destino or '').strip().upper() or None,
        pendencia_id=pendencia_id,
        custo_unitario=custo,
        custo_total=(qtd * custo).quantize(Decimal('0.01')),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
        dados_extras=sanitize_for_json({}),
    )
    if ficha.categoria == PENDENCIA_CATEGORIA_VENDA and receita_unitaria is not None:
        rec = Decimal(str(receita_unitaria))
        mov.receita_unitaria = rec
        mov.receita_total = (qtd * rec).quantize(Decimal('0.01'))

    db.session.add(mov)
    db.session.flush()
    return mov


def canibalizar(
    *, peca_id, quantidade, chassi_origem, chassi_destino, pendencia_id,
    operador_id, receita_unitaria=None,
):
    """Transfere peca de outra moto (CANIBALIZACAO, delta 0, custo 0) E abre uma
    FALTA_PECA ROOT no doador — a falta "viaja" (O4). Transacao unica.

    Guard: chassi_origem (doador) != chassi_destino (receptor). Se a ficha
    atendida e categoria=VENDA e receita_unitaria informada, grava receita na
    linha. add + flush, SEM commit.
    """
    from app.motos_assai.models import (
        AssaiPendencia, AssaiEstoqueMovimento, MOVIMENTO_CANIBALIZACAO,
        PENDENCIA_CATEGORIA_VENDA, PENDENCIA_CATEGORIA_FALTA_PECA,
        PENDENCIA_ORIGEM_GALPAO,
    )

    origem = (chassi_origem or '').strip().upper()
    destino = (chassi_destino or '').strip().upper()
    if not origem or not destino:
        raise EstoqueError('chassi_origem e chassi_destino obrigatorios.')
    if origem == destino:
        raise EstoqueError('Chassi doador nao pode ser igual ao receptor.')
    qtd = Decimal(str(quantidade))
    if qtd <= 0:
        raise EstoqueError('Quantidade deve ser positiva.')
    _exigir_peca(peca_id)
    from app.motos_assai.models import AssaiMoto, PENDENCIA_CATEGORIA_FALTA_PECA
    if not AssaiMoto.query.filter_by(chassi=origem).first():
        raise EstoqueError(f'Doador {origem} nao encontrado em assai_moto.')
    # doador nao pode estar FORA do estoque: abrir FALTA_PECA fisica (evento
    # PENDENTE) num doador FATURADO/SEPARADO/CANCELADO/... ressuscitaria uma moto
    # ja vendida. (status None ou efetivo-montada REVERTIDA/PENDENCIA_RESOLVIDA e' ok.)
    status_doador = status_efetivo(origem)
    if status_doador in EVENTOS_FORA_ESTOQUE:
        raise EstoqueError(
            f'Doador {origem} nao esta em estoque (status atual: {status_doador}); '
            'nao pode ser canibalizado.')
    # anti-cascata A->B->A: doador ja tem FALTA_PECA aberta DESTA peca
    ja_falta = (
        AssaiPendencia.query.filter(
            AssaiPendencia.chassi == origem,
            AssaiPendencia.peca_id == peca_id,
            AssaiPendencia.categoria == PENDENCIA_CATEGORIA_FALTA_PECA,
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        ).first()
    )
    if ja_falta is not None:
        raise EstoqueError(
            f'Cascata bloqueada: doador {origem} ja tem FALTA_PECA aberta desta peca.'
        )
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise EstoqueError(f'Pendencia {pendencia_id} nao encontrada.')

    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_CANIBALIZACAO,
        quantidade=qtd,
        delta_almoxarifado=Decimal('0'),
        chassi_origem=origem,
        chassi_destino=destino,
        pendencia_id=pendencia_id,
        custo_unitario=Decimal('0'),
        custo_total=Decimal('0'),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
        dados_extras=sanitize_for_json({'custo_estimado': True}),
    )
    if ficha.categoria == PENDENCIA_CATEGORIA_VENDA and receita_unitaria is not None:
        rec = Decimal(str(receita_unitaria))
        mov.receita_unitaria = rec
        mov.receita_total = (qtd * rec).quantize(Decimal('0.01'))

    db.session.add(mov)
    db.session.flush()

    # A falta "viaja": FALTA_PECA root no doador (origem/descricao default — ambos NOT NULL).
    # Import LAZY para evitar import circular (movimento_service <-> pendencia_service).
    from app.motos_assai.services.pendencia_service import abrir_pendencia
    abrir_pendencia(
        chassi=origem,
        categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
        origem=PENDENCIA_ORIGEM_GALPAO,
        descricao=f'Peca canibalizada para chassi {destino}',
        peca_id=peca_id,
        operador_id=operador_id,
        detalhes={'movimento_origem_id': mov.id, 'canibalizado_para': destino},
    )
    return mov
