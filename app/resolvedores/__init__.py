"""app.resolvedores — SoT da resolucao de entidades de negocio por nome/termo.

Consolida a logica antes duplicada em:
- .claude/skills/gerindo-expedicao/scripts/resolver_entidades.py (monolito, ORM, vivo)
- .claude/skills/resolvendo-entidades/scripts/*.py (split, raw SQL, CLI)

Arquitetura (spec 2026-06-01): nucleo compartilhado + 2 fachadas finas.
- Funcoes "ricas" (estilo monolito) servem o shim Python dos 9 importadores.
- Funcoes "*_cli" (estilo split, JSON achatado, fonte entregas) servem os 7 CLIs / 8 subagentes.

A API publica e re-exportada abaixo.
"""
# Nucleo (puro)
from app.resolvedores.normalizacao import normalizar_texto, _normalizar_token
from app.resolvedores.constantes import GRUPOS_EMPRESARIAIS, UFS_VALIDAS, ABREVIACOES_PRODUTO
from app.resolvedores.formatacao import formatar_sugestao_pedido, formatar_sugestao_produto

# Grupo (helpers puros + fachadas)
from app.resolvedores.grupo import (
    get_prefixos_grupo,
    listar_grupos_disponiveis,
    resolver_grupo,
    resolver_grupo_cli,
)

# Produto
from app.resolvedores.produto import (
    resolver_produto,
    resolver_produto_unico,
    resolver_produtos_na_carteira_cliente,
    resolver_produto_cli,
)

# Pedido
from app.resolvedores.pedido import resolver_pedido, resolver_pedido_cli

# Cliente
from app.resolvedores.cliente import resolver_cliente, resolver_cliente_cli

# Cidade
from app.resolvedores.cidade import (
    resolver_cidade,
    resolver_cidades_multiplas,
    resolver_cidade_cli,
)

# UF
from app.resolvedores.uf import resolver_uf, resolver_uf_cli

# Transportadora (port da split — unica entidade so-cli)
from app.resolvedores.transportadora import resolver_transportadora

__all__ = [
    # nucleo
    'normalizar_texto', '_normalizar_token',
    'GRUPOS_EMPRESARIAIS', 'UFS_VALIDAS', 'ABREVIACOES_PRODUTO',
    'formatar_sugestao_pedido', 'formatar_sugestao_produto',
    'get_prefixos_grupo', 'listar_grupos_disponiveis',
    # ricas (servem o shim dos 9 importadores)
    'resolver_produto', 'resolver_produto_unico', 'resolver_produtos_na_carteira_cliente',
    'resolver_pedido', 'resolver_cliente',
    'resolver_cidade', 'resolver_cidades_multiplas',
    'resolver_grupo', 'resolver_uf',
    # fachadas CLI (servem os 7 scripts / 8 subagentes)
    'resolver_produto_cli', 'resolver_pedido_cli', 'resolver_cliente_cli',
    'resolver_cidade_cli', 'resolver_grupo_cli', 'resolver_uf_cli', 'resolver_transportadora',
]
