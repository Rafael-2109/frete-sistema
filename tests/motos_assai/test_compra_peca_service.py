import re
import uuid
from decimal import Decimal

import pytest
from app import db
from app.motos_assai.models import (
    AssaiPecaCompra, AssaiPecaCompraItem,
    COMPRA_PECA_TIPO_COMPRA, COMPRA_PECA_TIPO_GARANTIA,
    COMPRA_PECA_STATUS_ABERTA, COMPRA_PECA_STATUS_PARCIAL,
    COMPRA_PECA_STATUS_RECEBIDA, COMPRA_PECA_STATUS_CANCELADA,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import saldo
from app.motos_assai.services.compra_peca_service import (
    criar_compra, adicionar_item, receber_item, cancelar_compra, CompraPecaError,
)


def _peca(admin_user):
    return criar_peca(nome=f'PECA_{uuid.uuid4().hex[:8].upper()}', operador_id=admin_user.id)


def test_criar_compra_gera_numero(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p.id, 'quantidade': 5}],
                         operador_id=admin_user.id)
        assert re.match(r'^PC-\d{4}-\d{4}$', c.numero)
        assert c.status == COMPRA_PECA_STATUS_ABERTA
        assert c.tipo == COMPRA_PECA_TIPO_COMPRA
        assert len(c.itens) == 1
        db.session.rollback()


def test_numeros_sao_unicos(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c1 = criar_compra(tipo=COMPRA_PECA_TIPO_GARANTIA,
                          itens=[{'peca_id': p.id, 'quantidade': 1}], operador_id=admin_user.id)
        c2 = criar_compra(tipo=COMPRA_PECA_TIPO_GARANTIA,
                          itens=[{'peca_id': p.id, 'quantidade': 1}], operador_id=admin_user.id)
        assert c1.numero != c2.numero
        db.session.rollback()


def test_numero_usa_sequence_global_nao_count(app, admin_user):
    # Discriminante sequence vs COUNT(): duas chamadas a _gerar_numero SEM inserir
    # linha entre elas. Com COUNT(linhas) os dois numeros seriam iguais; com nextval
    # o segundo e estritamente o sucessor (+1). Prova o §13.4 ("NUNCA COUNT()").
    from app.motos_assai.services.compra_peca_service import _gerar_numero
    with app.app_context():
        n1 = _gerar_numero()
        n2 = _gerar_numero()
        assert re.match(r'^PC-\d{4}-\d{4,}$', n1)
        assert n1 != n2
        seq1 = int(n1.rsplit('-', 1)[1])
        seq2 = int(n2.rsplit('-', 1)[1])
        assert seq2 == seq1 + 1
        db.session.rollback()


def test_receber_item_parcial_depois_total(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p.id, 'quantidade': 10}], operador_id=admin_user.id)
        item = c.itens[0]
        receber_item(compra_item_id=item.id, quantidade=4, custo_unitario='3.00', operador_id=admin_user.id)
        assert c.status == COMPRA_PECA_STATUS_PARCIAL
        assert item.quantidade_recebida == Decimal('4.000')
        assert saldo(p.id) == Decimal('4.000')
        receber_item(compra_item_id=item.id, quantidade=6, custo_unitario='3.00', operador_id=admin_user.id)
        assert c.status == COMPRA_PECA_STATUS_RECEBIDA
        assert saldo(p.id) == Decimal('10.000')
        db.session.rollback()


def test_adicionar_item(app, admin_user):
    with app.app_context():
        p1 = _peca(admin_user)
        p2 = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p1.id, 'quantidade': 1}], operador_id=admin_user.id)
        adicionar_item(compra_id=c.id, peca_id=p2.id, quantidade=2, custo_estimado='8.00')
        assert len(c.itens) == 2
        db.session.rollback()


def test_cancelar_compra(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p.id, 'quantidade': 1}], operador_id=admin_user.id)
        cancelar_compra(compra_id=c.id, operador_id=admin_user.id)
        assert c.status == COMPRA_PECA_STATUS_CANCELADA
        cancelar_compra(compra_id=c.id, operador_id=admin_user.id)  # idempotente
        assert c.status == COMPRA_PECA_STATUS_CANCELADA
        db.session.rollback()


def test_criar_compra_tipo_invalido_falha(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        with pytest.raises(CompraPecaError):
            criar_compra(tipo='XPTO', itens=[{'peca_id': p.id, 'quantidade': 1}],
                         operador_id=admin_user.id)
        db.session.rollback()
