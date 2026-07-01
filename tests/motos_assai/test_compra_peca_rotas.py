import re
import uuid

from app import db
from app.motos_assai.models import AssaiPecaCompra, AssaiPecaCompraItem
from app.motos_assai.services.peca_service import criar_peca


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
