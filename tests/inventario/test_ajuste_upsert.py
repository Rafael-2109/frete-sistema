"""Testes do endpoint inline UPSERT de ajustes manuais (POST /upsert).

NOTA: o endpoint /upsert chama db.session.commit() (route Flask comum).
Isso escapa do SAVEPOINT do fixture `db`, persistindo no banco. Por isso
usamos `codigo` unico por teste + teardown cirurgico via raw SQL.
"""
import uuid
from datetime import date
from decimal import Decimal
import pytest
from app import db as _db
from app.inventario.models import AjusteManualInventario, CicloInventario


@pytest.fixture(autouse=True)
def _app_ctx(app):
    """Mantem app_context ativo durante o teste todo (necessario para Model.query)."""
    with app.app_context():
        yield


@pytest.fixture
def admin_user(app):
    """Cria usuario admin com email unico, commita, e remove no teardown."""
    from app.auth.models import Usuario
    from werkzeug.security import generate_password_hash
    email = f'admin-inv-{uuid.uuid4().hex[:8]}@bot.local'
    u = Usuario(
        nome='Test Admin', email=email,
        senha_hash=generate_password_hash('x'), perfil='administrador',
        status='ativo',
    )
    _db.session.add(u)
    _db.session.commit()
    user_id = u.id
    yield user_id
    _db.session.execute(
        _db.text('DELETE FROM usuarios WHERE id = :i'), {'i': user_id})
    _db.session.commit()


@pytest.fixture
def ciclo_isolado(app):
    """Cria CicloInventario com codigo unico, commita, e remove no teardown."""
    codigo = f'TEST-UPSERT-{uuid.uuid4().hex[:8]}'
    c = CicloInventario(
        codigo=codigo, data_snapshot=date(2026, 5, 16),
        descricao='Test upsert', status='ATIVO', criado_por='pytest',
    )
    _db.session.add(c)
    _db.session.commit()
    ciclo_id = c.id
    yield ciclo_id
    _db.session.execute(
        _db.text('DELETE FROM inventario_ajuste_manual WHERE ciclo_id = :i'),
        {'i': ciclo_id})
    _db.session.execute(
        _db.text('DELETE FROM inventario_ciclo WHERE id = :i'), {'i': ciclo_id})
    _db.session.commit()


@pytest.fixture
def admin_client(client, admin_user):
    """Client autenticado como admin."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user)
        sess['_fresh'] = True
    return client


def _upsert(client, ciclo_id, **form):
    return client.post(
        f'/inventario/ajustes/{ciclo_id}/upsert',
        data=form, headers={'X-CSRFToken': 'test-bypass'},
    )


def test_upsert_insert_cria_registro(admin_client, ciclo_isolado, app):
    r = _upsert(admin_client, ciclo_isolado, cod_produto='4320147',
                local='Estoque', qtd='100.5')
    assert r.status_code == 201, r.data
    data = r.get_json()
    assert data['mode'] == 'insert'
    aj = AjusteManualInventario.query.filter_by(
        ciclo_id=ciclo_isolado, cod_produto='4320147').one()
    assert aj.local == 'Estoque'
    assert aj.qtd == Decimal('100.5')


def test_upsert_update_atualiza_existente(admin_client, ciclo_isolado, app):
    _upsert(admin_client, ciclo_isolado, cod_produto='4320147', local='A', qtd='10')
    r = _upsert(admin_client, ciclo_isolado, cod_produto='4320147',
                local='B', qtd='25')
    assert r.status_code == 200, r.data
    assert r.get_json()['mode'] == 'update'
    rows = AjusteManualInventario.query.filter_by(
        ciclo_id=ciclo_isolado, cod_produto='4320147').all()
    assert len(rows) == 1, 'upsert deve manter exatamente 1 registro por cod'
    assert rows[0].local == 'B'
    assert rows[0].qtd == Decimal('25')


def test_upsert_qtd_vazia_deleta(admin_client, ciclo_isolado, app):
    _upsert(admin_client, ciclo_isolado, cod_produto='4320147', local='A', qtd='10')
    r = _upsert(admin_client, ciclo_isolado, cod_produto='4320147',
                local='', qtd='')
    assert r.status_code == 200, r.data
    assert r.get_json()['deleted'] == 1
    rows = AjusteManualInventario.query.filter_by(
        ciclo_id=ciclo_isolado, cod_produto='4320147').all()
    assert rows == []


def test_upsert_qtd_zero_deleta(admin_client, ciclo_isolado, app):
    _upsert(admin_client, ciclo_isolado, cod_produto='4320147', local='A', qtd='10')
    r = _upsert(admin_client, ciclo_isolado, cod_produto='4320147',
                local='A', qtd='0')
    assert r.status_code == 200, r.data
    assert r.get_json()['deleted'] == 1
    assert AjusteManualInventario.query.filter_by(
        ciclo_id=ciclo_isolado, cod_produto='4320147').count() == 0


def test_upsert_consolida_duplicatas_em_um(admin_client, ciclo_isolado, app):
    """Se ja existem 2+ registros legacy para o mesmo cod, upsert mantem 1."""
    from datetime import datetime, timedelta
    base = datetime(2026, 5, 1, 10, 0)
    for i, q in enumerate([10, 20, 30]):
        _db.session.add(AjusteManualInventario(
            ciclo_id=ciclo_isolado, cod_produto='4320147', local=f'X{i}',
            qtd=Decimal(q), criado_em=base + timedelta(hours=i),
            atualizado_em=base + timedelta(hours=i),
        ))
    _db.session.commit()
    assert AjusteManualInventario.query.filter_by(
        ciclo_id=ciclo_isolado, cod_produto='4320147').count() == 3

    r = _upsert(admin_client, ciclo_isolado, cod_produto='4320147',
                local='Final', qtd='99')
    assert r.status_code == 200, r.data
    assert r.get_json()['mode'] == 'update'
    rows = AjusteManualInventario.query.filter_by(
        ciclo_id=ciclo_isolado, cod_produto='4320147').all()
    assert len(rows) == 1, 'duplicatas legacy devem ser consolidadas'
    assert rows[0].local == 'Final'
    assert rows[0].qtd == Decimal('99')


def test_upsert_sem_cod_produto_retorna_400(admin_client, ciclo_isolado, app):
    r = _upsert(admin_client, ciclo_isolado, cod_produto='', local='A', qtd='10')
    assert r.status_code == 400
    assert 'cod_produto' in (r.get_json().get('erro') or '').lower()


def test_upsert_qtd_invalida_retorna_400(admin_client, ciclo_isolado, app):
    r = _upsert(admin_client, ciclo_isolado, cod_produto='4320147',
                local='A', qtd='abc')
    assert r.status_code == 400
    assert 'qtd' in (r.get_json().get('erro') or '').lower()
