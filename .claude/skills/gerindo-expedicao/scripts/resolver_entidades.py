#!/usr/bin/env python3
"""SHIM de compatibilidade — resolver_entidades.py.

A logica foi consolidada em `app.resolvedores` (Onda D, 2026-06-01). Este arquivo agora apenas
re-exporta a API para os 9 importadores Python que dependem do nome `resolver_entidades`:
  - 7 scripts irmaos de gerindo-expedicao/scripts/
  - 2 scripts de visao-produto/scripts/ (via sys.path hardcoded `../../gerindo-expedicao/scripts`)

Os contratos sao preservados 1:1 (tupla p/ resolver_pedido; tupla p/ resolver_produto_unico;
list p/ resolver_produto; dicts ricos p/ resolver_cliente/grupo/uf/cidade; constantes).

Codigo morto pos-refactor (detectar_abreviacoes, get_abreviacao_produto) NAO foi reexportado —
grep ao vivo (2026-06-01) confirmou zero callers. A logica de abreviacao vive em
app.embeddings.product_search (SoT de runtime), reusada por app.resolvedores.

Detalhes: docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md
"""
import sys
import os

# Garante que 'app' seja importavel quando este shim e importado por scripts standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Re-exporta a API publica canonica (constantes + funcoes ricas + fachadas *_cli)
from app.resolvedores import *  # noqa: F401,F403,E402
from app.resolvedores import __all__ as __all__  # noqa: E402
