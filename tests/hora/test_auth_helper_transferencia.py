"""Valida helper loja_origem_permitida_para_transferencia."""
from unittest.mock import patch, MagicMock


def _mock_user(perfil, loja_hora_id):
    u = MagicMock()
    u.perfil = perfil
    u.loja_hora_id = loja_hora_id
    u.is_authenticated = True
    return u


def test_admin_pode_escolher_qualquer_origem(app):
    from app.hora.services.auth_helper import loja_origem_permitida_para_transferencia
    with app.test_request_context():
        with patch('app.hora.services.auth_helper.current_user', _mock_user('administrador', None)):
            assert loja_origem_permitida_para_transferencia() is None


def test_escopado_recebe_sua_loja(app):
    from app.hora.services.auth_helper import loja_origem_permitida_para_transferencia
    with app.test_request_context():
        with patch('app.hora.services.auth_helper.current_user', _mock_user('operador', 42)):
            assert loja_origem_permitida_para_transferencia() == 42


def test_usuario_sem_loja_retorna_none(app):
    from app.hora.services.auth_helper import loja_origem_permitida_para_transferencia
    with app.test_request_context():
        with patch('app.hora.services.auth_helper.current_user', _mock_user('operador', None)):
            assert loja_origem_permitida_para_transferencia() is None
