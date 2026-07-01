import uuid
from decimal import Decimal

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


def test_editar_preserva_custo_br_roundtrip(login_admin, app):
    """Finding 1 (CRITICAL): editar sem retocar o custo NÃO pode inflar 10.000x."""
    nome = f'PZBR{uuid.uuid4().hex[:6].upper()}'
    with app.app_context():
        mid = AssaiModelo.query.filter_by(codigo='DOT').first().id
    resp = login_admin.post('/motos-assai/pecas/novo', data={
        'nome': nome, 'codigo': '', 'custo_referencia': '12,50',
        'ativo': 'y', 'modelo_ids': [mid]})
    assert resp.status_code in (302, 200)
    with app.app_context():
        p = AssaiPeca.query.filter_by(nome=nome).first()
        assert p is not None
        assert p.custo_referencia == Decimal('12.50')
        pid = p.id

    resp = login_admin.get(f'/motos-assai/pecas/{pid}/editar')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert '12,50' in html
    assert '125000' not in html  # não deve ter vazado o valor inflado

    novo_nome = nome + '-EDITADO'
    resp = login_admin.post(f'/motos-assai/pecas/{pid}/editar', data={
        'nome': novo_nome, 'codigo': '', 'custo_referencia': '12,50',
        'ativo': 'y', 'modelo_ids': [mid]})
    assert resp.status_code in (302, 200)

    with app.app_context():
        p = db.session.get(AssaiPeca, pid)
        assert p.nome == novo_nome
        assert p.custo_referencia == Decimal('12.50'), (
            f'custo_referencia inflou: {p.custo_referencia}')
        db.session.delete(p); db.session.commit()


def test_custo_invalido_nao_500(login_admin, app):
    """Finding 2 (IMPORTANT): custo malformado deve dar erro gracioso, não 500."""
    nome = f'PZINV{uuid.uuid4().hex[:6].upper()}'
    resp = login_admin.post('/motos-assai/pecas/novo', data={
        'nome': nome, 'codigo': '', 'custo_referencia': 'abc',
        'ativo': 'y', 'modelo_ids': []})
    assert resp.status_code in (200, 302)
    with app.app_context():
        p = AssaiPeca.query.filter_by(nome=nome).first()
        assert p is None


def test_lista_filtra_ativo(login_admin, app, admin_user):
    """Finding 3 (IMPORTANT): GET /pecas deve filtrar por ativo, não só por `q`."""
    nome_ativo = f'PZATIVA{uuid.uuid4().hex[:6].upper()}'
    nome_inativo = f'PZINATIVA{uuid.uuid4().hex[:6].upper()}'
    with app.app_context():
        uid = admin_user.id
        p_ativa = AssaiPeca(nome=nome_ativo, ativo=True, criado_por_id=uid)
        p_inativa = AssaiPeca(nome=nome_inativo, ativo=False, criado_por_id=uid)
        db.session.add_all([p_ativa, p_inativa])
        db.session.commit()
        id_ativa, id_inativa = p_ativa.id, p_inativa.id

    try:
        resp = login_admin.get('/motos-assai/pecas?ativos=1')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert nome_ativo in html
        assert nome_inativo not in html

        resp = login_admin.get('/motos-assai/pecas')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert nome_ativo in html
        assert nome_inativo in html
    finally:
        with app.app_context():
            for pid in (id_ativa, id_inativa):
                p = db.session.get(AssaiPeca, pid)
                if p:
                    db.session.delete(p)
            db.session.commit()
