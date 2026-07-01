import uuid
from app import db
from app.motos_assai.models import AssaiPeca, AssaiModelo


def test_lista_pecas_200(login_admin):
    assert login_admin.get('/motos-assai/pecas').status_code == 200


def test_criar_peca_via_post(login_admin, app):
    nome = f'PZROTA{uuid.uuid4().hex[:6].upper()}'
    with app.app_context():
        mid = AssaiModelo.query.filter_by(codigo='DOT').first().id
    resp = login_admin.post('/motos-assai/pecas/novo', data={
        'nome': nome, 'codigo': 'C1', 'custo_referencia': '12,50',
        'ativo': 'y', 'modelo_ids': [mid]})
    assert resp.status_code in (302, 200)
    with app.app_context():
        p = AssaiPeca.query.filter_by(nome=nome).first()
        assert p is not None and len(p.modelos) == 1
        db.session.delete(p); db.session.commit()
