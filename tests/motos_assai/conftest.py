import pytest
from app import create_app, db
from app.auth.models import Usuario


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        u = Usuario.query.filter_by(perfil='administrador').first()
        assert u, "Pré-requisito: ter pelo menos 1 admin no banco"
        yield u


@pytest.fixture
def login_admin(client, admin_user):
    with client.session_transaction() as s:
        s['_user_id'] = str(admin_user.id)
        s['_fresh'] = True
    return client
