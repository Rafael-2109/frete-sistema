"""Blueprint principal do módulo HORA (Lojas Motochefe).

Todas as rotas vivem sob `/hora/*`. Templates em `app/templates/hora/`.
Ver app/hora/CLAUDE.md para convenções.
"""
from flask import Blueprint

hora_bp = Blueprint(
    'hora',
    __name__,
    url_prefix='/hora',
    template_folder='../../templates/hora',
)

# Imports das rotas APÓS criar blueprint (evita import circular).
from . import (  # noqa: E402, F401
    dashboard,
    cadastros,
    pedidos,
    nfs,
    recebimentos,
    permissoes,
    estoque,
    devolucoes,
    pecas,
    transferencias,
    avarias,
)


__all__ = ['hora_bp']
