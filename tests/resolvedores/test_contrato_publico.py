"""TDD — contrato da API publica de app.resolvedores (re-exports do __init__).

Garante que o shim do monolito (9 importadores) e os wrappers CLI (8 subagentes) conseguem
importar todos os simbolos que precisam de um unico lugar.
"""
import app.resolvedores as R

# Simbolos que os 9 importadores Python do monolito usam (devem existir p/ o shim re-exportar)
USADOS_PELO_MONOLITO = [
    'GRUPOS_EMPRESARIAIS', 'get_prefixos_grupo', 'listar_grupos_disponiveis',
    'resolver_pedido', 'formatar_sugestao_pedido', 'resolver_produto_unico',
    'formatar_sugestao_produto', 'resolver_produto', 'resolver_produtos_na_carteira_cliente',
    'resolver_cliente', 'normalizar_texto',
]

# Fachadas CLI (7 scripts / 8 subagentes)
FACHADAS_CLI = [
    'resolver_produto_cli', 'resolver_pedido_cli', 'resolver_cliente_cli',
    'resolver_cidade_cli', 'resolver_grupo_cli', 'resolver_uf_cli', 'resolver_transportadora',
]

# Restante da API rica re-exportada para compat total do shim
RICAS_EXTRA = [
    'resolver_cidade', 'resolver_cidades_multiplas', 'resolver_grupo', 'resolver_uf',
    '_normalizar_token', 'UFS_VALIDAS', 'ABREVIACOES_PRODUTO',
]


def test_simbolos_usados_pelo_monolito_existem():
    for nome in USADOS_PELO_MONOLITO:
        assert hasattr(R, nome), f"{nome} ausente em app.resolvedores"


def test_fachadas_cli_existem_e_chamaveis():
    for nome in FACHADAS_CLI:
        assert hasattr(R, nome), f"{nome} ausente"
        assert callable(getattr(R, nome))


def test_api_rica_extra_existe():
    for nome in RICAS_EXTRA:
        assert hasattr(R, nome), f"{nome} ausente"


def test_from_import_direto_funciona():
    from app.resolvedores import resolver_pedido, resolver_produto_cli, resolver_transportadora
    assert callable(resolver_pedido)
    assert callable(resolver_produto_cli)
    assert callable(resolver_transportadora)
