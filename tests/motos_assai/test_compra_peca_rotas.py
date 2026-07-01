import re
import uuid
from decimal import Decimal

from app import db
from app.motos_assai.models import (
    AssaiEstoqueMovimento, AssaiPeca, AssaiPecaCompra, AssaiPecaCompraItem,
    COMPRA_PECA_STATUS_PARCIAL, COMPRA_PECA_TIPO_COMPRA,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import saldo
from app.motos_assai.services.compra_peca_service import criar_compra


def _limpar_peca(app, pid):
    """Limpa a peça de teste + seu ledger + compras (FK ondelete='RESTRICT' em
    assai_estoque_movimento.peca_id e assai_peca_compra_item.peca_id exige apagar
    movimentações e compras antes da peça — espelha `test_estoque_peca_rotas.py`)."""
    with app.app_context():
        AssaiEstoqueMovimento.query.filter_by(peca_id=pid).delete()
        for item in AssaiPecaCompraItem.query.filter_by(peca_id=pid).all():
            db.session.delete(item.compra)  # cascade apaga os itens da mesma compra
        db.session.flush()
        p = db.session.get(AssaiPeca, pid)
        if p:
            db.session.delete(p)
        db.session.commit()


def test_lista_compras_200(login_admin):
    assert login_admin.get('/motos-assai/compras-peca').status_code == 200


def test_criar_compra_via_post(login_admin, app, admin_user):
    with app.app_context():
        p = criar_peca(nome=f'PZC{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit(); pid = p.id
    resp = login_admin.post('/motos-assai/compras-peca/nova', data={
        'tipo': 'COMPRA', 'fornecedor': 'MOTOCHEFE',
        'peca_id': [pid], 'quantidade': ['3'], 'custo_estimado': ['9,00']})
    assert resp.status_code in (302, 200)
    with app.app_context():
        c = AssaiPecaCompra.query.order_by(AssaiPecaCompra.id.desc()).first()
        assert re.match(r'^PC-\d{4}-\d{4,}$', c.numero) and len(c.itens) == 1


def test_detalhe_404_compra_inexistente(login_admin):
    resp = login_admin.get('/motos-assai/compras-peca/999999999', follow_redirects=True)
    assert resp.status_code == 200  # redireciona para lista com flash


def test_criar_compra_malformada_nao_500(login_admin, app, admin_user):
    """Espelha a lição dos Tasks 10/11: quantidade/custo malformado deve dar
    flash gracioso, não estourar 500 nem criar a compra."""
    with app.app_context():
        p = criar_peca(nome=f'PZCBAD{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit(); pid = p.id
    resp = login_admin.post('/motos-assai/compras-peca/nova', data={
        'tipo': 'COMPRA', 'fornecedor': 'MOTOCHEFE',
        'peca_id': [pid], 'quantidade': ['abc'], 'custo_estimado': ['9,00']})
    assert resp.status_code in (302, 200)
    with app.app_context():
        # Nenhum item de compra deve ter sido persistido para essa peça
        # (rollback ao capturar CompraPecaError/InvalidOperation na rota).
        assert AssaiPecaCompraItem.query.filter_by(peca_id=pid).count() == 0


def test_receber_item_entra_no_ledger(login_admin, app, admin_user):
    with app.app_context():
        p = criar_peca(nome=f'PZR{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit(); pid = p.id
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': pid, 'quantidade': 5}], operador_id=admin_user.id)
        db.session.commit(); cid = c.id; item_id = c.itens[0].id
    try:
        resp = login_admin.post(f'/motos-assai/compras-peca/{cid}/receber-item', data={
            'compra_item_id': item_id, 'quantidade': '3', 'custo_unitario': '10,00'})
        assert resp.status_code in (200, 302)
        with app.app_context():
            assert saldo(pid) == Decimal('3.000')
            assert db.session.get(AssaiPecaCompra, cid).status == COMPRA_PECA_STATUS_PARCIAL
    finally:
        _limpar_peca(app, pid)


def test_receber_item_custo_invalido_nao_500(login_admin, app, admin_user):
    """Espelha a lição do Task 12 review: custo_unitario malformado no
    receber-item levanta EstoqueError (não CompraPecaError) dentro de
    movimento_service.registrar_entrada — precisa virar flash gracioso, não 500,
    e não pode gravar ENTRADA parcial no ledger."""
    with app.app_context():
        p = criar_peca(nome=f'PZRBAD{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit(); pid = p.id
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': pid, 'quantidade': 5}], operador_id=admin_user.id)
        db.session.commit(); cid = c.id; item_id = c.itens[0].id
    try:
        resp = login_admin.post(f'/motos-assai/compras-peca/{cid}/receber-item', data={
            'compra_item_id': item_id, 'quantidade': '3', 'custo_unitario': 'abc'})
        assert resp.status_code in (200, 302)
        with app.app_context():
            assert saldo(pid) == Decimal('0')
    finally:
        _limpar_peca(app, pid)
