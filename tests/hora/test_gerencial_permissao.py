"""Permissão e escopo da seção Gerencial HORA (F1)."""


def test_slugs_gerencial_registrados():
    """Os 2 slugs novos existem em MODULOS_HORA e são só-ver (MODULOS_SO_VER)."""
    from app.hora.models.permissao import MODULOS_HORA, MODULOS_SO_VER
    slugs = [m[0] for m in MODULOS_HORA]
    assert 'gerencial' in slugs
    assert 'gerencial_relatorios' in slugs
    assert 'gerencial' in MODULOS_SO_VER
    assert 'gerencial_relatorios' in MODULOS_SO_VER


def test_validar_modulo_aceita_slugs_gerencial():
    """tem_perm_hora não deve rejeitar os slugs novos como módulo inválido."""
    from app.hora.services.permissao_service import _validar_modulo
    # não levanta ValueError
    _validar_modulo('gerencial')
    _validar_modulo('gerencial_relatorios')


_ROTAS_GERENCIAL = {
    'hora.gerencial_index': '/hora/gerencial',
    'hora.gerencial_executivo': '/hora/gerencial/executivo',
    'hora.gerencial_comercial': '/hora/gerencial/comercial',
    'hora.gerencial_estoque': '/hora/gerencial/estoque',
    'hora.gerencial_suprimento': '/hora/gerencial/suprimento',
    'hora.gerencial_relatorios': '/hora/gerencial/relatorios',
}


def test_url_for_rotas_gerencial_resolvem(app):
    """Todas as rotas da seção Gerencial resolvem sem BuildError."""
    from flask import url_for
    with app.test_request_context():
        for endpoint, path in _ROTAS_GERENCIAL.items():
            assert url_for(endpoint) == path, f'{endpoint} != {path}'


def test_rotas_gerencial_respondem(app):
    """Rotas registradas respondem (anônimo: redirect/403 — nunca 404/500)."""
    c = app.test_client()
    for path in _ROTAS_GERENCIAL.values():
        r = c.get(path)
        assert r.status_code in (200, 302, 401, 403), f'{path} -> {r.status_code}'


def test_base_gerencial_template_compila(app):
    """Layout base da seção carrega sem erro de Jinja."""
    app.jinja_env.get_template('hora/gerencial/base_gerencial.html')
