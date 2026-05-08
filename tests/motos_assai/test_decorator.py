from app.auth.models import Usuario


def test_decorator_redireciona_sem_login(client):
    r = client.get('/motos-assai/', follow_redirects=False)
    assert r.status_code in (302, 308)
    assert '/auth/login' in r.location


def test_pode_acessar_motos_assai_sem_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='ativo', sistema_motos_assai=False, perfil='vendedor')
        assert u.pode_acessar_motos_assai() is False


def test_pode_acessar_motos_assai_com_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='ativo', sistema_motos_assai=True, perfil='vendedor')
        assert u.pode_acessar_motos_assai() is True


def test_status_nao_ativo_bloqueia_mesmo_com_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='pendente', sistema_motos_assai=True, perfil='vendedor')
        assert u.pode_acessar_motos_assai() is False


def test_admin_passa_sem_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='ativo', sistema_motos_assai=False, perfil='administrador')
        assert u.pode_acessar_motos_assai() is True


def test_admin_pendente_e_bloqueado(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='pendente', sistema_motos_assai=True, perfil='administrador')
        assert u.pode_acessar_motos_assai() is False
