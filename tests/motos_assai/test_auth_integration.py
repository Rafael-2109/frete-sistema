from app import db
from app.auth.models import Usuario
from app.auth.utils import url_primeiro_dashboard_disponivel


def test_redirect_pos_login_motos_assai_only(app):
    with app.app_context():
        u = Usuario(email='only@x', nome='Only', senha_hash='x',
                    status='ativo', sistema_motos_assai=True,
                    sistema_logistica=False, sistema_lojas=False,
                    sistema_motochefe=False, sistema_carvia=False,
                    perfil='vendedor')
        with app.test_request_context():
            url = url_primeiro_dashboard_disponivel(u)
        assert url and '/motos-assai' in url
