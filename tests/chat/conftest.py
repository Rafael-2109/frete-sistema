"""
Fixtures para testes do modulo chat in-app.

Usa app_context da sessao + rollback por funcao para isolamento.
"""
import pytest

from app import create_app, db
from app.auth.models import Usuario


@pytest.fixture(scope='module')
def app():
    application = create_app()
    with application.app_context():
        yield application


@pytest.fixture
def db_session(app):
    """
    Per-test rollback simples. Faz rollback apos cada teste.
    Nota: ThreadService usa commit() internamente, entao dados podem persistir
    entre testes. Cada teste usa emails unicos para evitar colisoes.
    """
    with app.app_context():
        yield db.session
        db.session.rollback()
        db.session.remove()


_user_counter = 0


def _mk_user(**kw):
    global _user_counter
    _user_counter += 1

    # Mapear kwargs shorthand para nomes reais do modelo Usuario
    sistema_carvia = kw.pop('carvia', False)
    sistema_motochefe = kw.pop('motochefe', False)

    defaults = dict(
        nome='Teste',
        email=f'u{_user_counter}@t.local',
        senha_hash='x' * 60,
        perfil='logistica',
        status='ativo',
        sistema_carvia=sistema_carvia,
        sistema_motochefe=sistema_motochefe,
        sistema_logistica=False,
        loja_hora_id=None,
    )
    defaults.update(kw)
    u = Usuario(**defaults)
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture
def user_factory(db_session):
    return _mk_user
