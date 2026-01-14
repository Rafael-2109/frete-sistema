"""
Módulo de Relatórios Fiscais
============================

Relatórios fiscais com campos IBS/CBS da reforma tributária.
Integração direta com Odoo para extração de dados.

Autor: Sistema de Fretes
Data: 2026-01-14
"""

from flask import Blueprint

relatorios_fiscais_bp = Blueprint(
    'relatorios_fiscais',
    __name__,
    url_prefix='/relatorios-fiscais'
)

from . import routes  # noqa: E402, F401
