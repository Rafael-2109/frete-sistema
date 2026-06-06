"""Smoke tests: rota de historico de notificacoes WhatsApp (H4)."""
import pytest


def test_lista_notificacoes_rota_existe(app):
    """Rota registrada e responde (sem autenticacao: redirect ou 401/403)."""
    c = app.test_client()
    r = c.get('/hora/tagplus/notificacoes')
    assert r.status_code in (200, 302, 401, 403)


def test_url_for_lista(app):
    """url_for resolve sem BuildError."""
    with app.test_request_context():
        from flask import url_for
        assert url_for('hora.tagplus_notificacoes_lista') == '/hora/tagplus/notificacoes'


def test_url_for_reenviar(app):
    """url_for do reenvio resolve com reg_id correto."""
    with app.test_request_context():
        from flask import url_for
        url = url_for('hora.tagplus_notificacao_reenviar', reg_id=42)
        assert url == '/hora/tagplus/notificacoes/42/reenviar'


def test_template_compila(app):
    """Template hora/tagplus/notificacoes.html carrega sem erros de Jinja."""
    app.jinja_env.get_template('hora/tagplus/notificacoes.html')
