"""Smoke: rotas de configuração do grupo WhatsApp por loja (1 grupo por loja)."""


def test_url_for_grupos_api(app):
    with app.test_request_context():
        from flask import url_for
        assert url_for('hora.lojas_grupos_whatsapp_api') == '/hora/lojas/api/grupos-whatsapp'


def test_url_for_salvar_grupo(app):
    with app.test_request_context():
        from flask import url_for
        assert url_for('hora.lojas_salvar_grupo_whatsapp', loja_id=7) == \
            '/hora/lojas/7/salvar-grupo-whatsapp'


def test_grupos_api_rota_existe(app):
    c = app.test_client()
    r = c.get('/hora/lojas/api/grupos-whatsapp')
    assert r.status_code in (200, 302, 401, 403)


def test_salvar_grupo_rota_existe(app):
    c = app.test_client()
    r = c.post('/hora/lojas/1/salvar-grupo-whatsapp',
               data={'whatsapp_grupo_jid': '120363@g.us'})
    assert r.status_code in (200, 302, 401, 403, 404)


def test_template_loja_detalhe_compila(app):
    """Template da loja (com o card de grupo WhatsApp) carrega sem erro de Jinja."""
    app.jinja_env.get_template('hora/lojas_detalhe.html')
