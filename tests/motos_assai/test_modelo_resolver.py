from app.motos_assai.services import resolver_modelo, resolver_por_codigo_qpa


def test_resolve_codigo_canonico(app):
    """X11_MINI já existe seeded."""
    with app.app_context():
        m = resolver_modelo('X11_MINI')
        assert m is not None
        assert m.codigo == 'X11_MINI'


def test_resolve_alias_x11_nac(app):
    """X11 NAC é alias seeded de X11_MINI."""
    with app.app_context():
        m = resolver_modelo('X11 NAC')
        assert m is not None
        assert m.codigo == 'X11_MINI'


def test_resolve_alias_case_insensitive(app):
    with app.app_context():
        m = resolver_modelo('x11 nac')
        assert m is not None
        assert m.codigo == 'X11_MINI'


def test_resolve_substring_descricao_qpa(app):
    """Substring de descricao_qpa pega quando texto é mais longo."""
    with app.app_context():
        m = resolver_modelo('AUTOPROPELIDO DOT 1000W 60V 20AH')
        assert m is not None
        assert m.codigo == 'DOT'


def test_resolve_codigo_qpa(app):
    with app.app_context():
        m = resolver_por_codigo_qpa('1342063')
        assert m is not None
        assert m.codigo == 'SOL'


def test_resolve_nao_encontrado(app):
    with app.app_context():
        m = resolver_modelo('MIA TURBO')
        assert m is None


def test_resolve_string_vazia(app):
    with app.app_context():
        assert resolver_modelo('') is None
        assert resolver_modelo(None) is None
        assert resolver_por_codigo_qpa('') is None
