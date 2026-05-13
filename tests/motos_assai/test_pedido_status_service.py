"""Testes para recalcular_status_pedido.

Spec: §14
Plano: Task 17

P2 fix 13 (2026-05-13): fixture local `app` removida — usa conftest.py global
para evitar conflito (fixture local com `db.create_all/drop_all` podia destruir
estado de outros testes em suite completa). Tests agora usam app_context manual.

Como o conftest global nao faz drop_all/create_all, cada teste:
- Gera identificadores unicos via _uid() para evitar colisao com banco persistente
- Faz db.session.rollback() ao final para nao deixar lixo
"""
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiPedidoVendaLoja,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiCd, AssaiLoja, AssaiModelo, AssaiMoto,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_FECHADA,
)
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _setup_pedido():
    """Cria pedido com 10 motos pedidas, IDs unicos.

    Deve ser chamado dentro de `with app.app_context()`. Retorna (pedido, modelo, loja).
    """
    uid = _uid()
    # Reusa Loja/Modelo se existem (seeded); senao cria com IDs unicos.
    # AssaiPedidoVenda NAO tem cd_id (era um bug do teste original — passava por
    # acaso pois fixture local com drop_all evitava o erro).
    loja = AssaiLoja.query.first()
    if not loja:
        loja = AssaiLoja(numero=int(uid[:4], 16) % 9000 + 1000,
                         cnpj=f'98765432{uid[:6]}', nome=f'Loja-TST-{uid}')
        db.session.add(loja); db.session.flush()

    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    if not modelo:
        modelo = AssaiModelo(codigo=f'TST_{uid[:4]}', regex_chassi=r'^TEST\d+$')
        db.session.add(modelo); db.session.flush()

    pedido = AssaiPedidoVenda(
        numero=f'TST-PSTAT-{uid}', status=PEDIDO_STATUS_ABERTO,
    )
    db.session.add(pedido); db.session.flush()

    pedido_loja = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pedido_loja); db.session.flush()

    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pedido_loja.id,
        loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=10, valor_unitario=1000.0, valor_total=10000.0,
    ))
    db.session.flush()
    return pedido, modelo, loja


def test_recalcular_zero_faturada_retorna_aberto(app, admin_user):
    with app.app_context():
        pedido, _modelo, _loja = _setup_pedido()
        recalcular_status_pedido(pedido.id)
        assert pedido.status == PEDIDO_STATUS_ABERTO
        db.session.rollback()


def test_recalcular_parcial_retorna_parcialmente_faturado(app, admin_user):
    with app.app_context():
        pedido, modelo, loja = _setup_pedido()

        # Criar sep FATURADA com 3 chassis (parcial: 3/10)
        sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                             status=SEPARACAO_STATUS_FATURADA)
        db.session.add(sep); db.session.flush()

        uid = _uid()
        for i in range(3):
            chassi = f'TEST{uid}P{i}'
            db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto'))
            db.session.flush()
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep.id, chassi=chassi, modelo_id=modelo.id,
                valor_unitario_qpa=1000.0,
            ))
        db.session.flush()

        recalcular_status_pedido(pedido.id)
        assert pedido.status == PEDIDO_STATUS_PARCIALMENTE_FATURADO
        db.session.rollback()


def test_recalcular_total_retorna_faturado(app, admin_user):
    with app.app_context():
        pedido, modelo, loja = _setup_pedido()

        sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                             status=SEPARACAO_STATUS_FATURADA)
        db.session.add(sep); db.session.flush()

        uid = _uid()
        for i in range(10):
            chassi = f'TEST{uid}T{i:02}'
            db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto'))
            db.session.flush()
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep.id, chassi=chassi, modelo_id=modelo.id,
                valor_unitario_qpa=1000.0,
            ))
        db.session.flush()

        recalcular_status_pedido(pedido.id)
        assert pedido.status == PEDIDO_STATUS_FATURADO
        db.session.rollback()


def test_recalcular_pedido_cancelado_nao_muda(app, admin_user):
    with app.app_context():
        pedido, _modelo, _loja = _setup_pedido()
        pedido.status = PEDIDO_STATUS_CANCELADO
        db.session.flush()

        recalcular_status_pedido(pedido.id)
        assert pedido.status == PEDIDO_STATUS_CANCELADO  # Status manual nao muda
        db.session.rollback()


def test_recalcular_sep_fechada_nao_conta(app, admin_user):
    """Sep FECHADA (sem NF batida) NAO conta como faturada."""
    with app.app_context():
        pedido, modelo, loja = _setup_pedido()

        sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                             status=SEPARACAO_STATUS_FECHADA)
        db.session.add(sep); db.session.flush()

        uid = _uid()
        for i in range(5):
            chassi = f'TEST{uid}F{i}'
            db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto'))
            db.session.flush()
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep.id, chassi=chassi, modelo_id=modelo.id,
                valor_unitario_qpa=1000.0,
            ))
        db.session.flush()

        recalcular_status_pedido(pedido.id)
        assert pedido.status == PEDIDO_STATUS_ABERTO  # FECHADA nao conta
        db.session.rollback()
