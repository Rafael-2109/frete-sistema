"""
Sistema de Permissões Simples
==============================

Sistema minimalista mas funcional para controle de acesso.

NOTA: `from . import routes` foi removido do topo por causa de circular
import (app.carteira.main_routes importa check_permission deste modulo,
e routes.py importa carteira indiretamente). O blueprint de permissoes
e registrado diretamente em app/__init__.py onde ja e feito o import
explicito de app.permissions.routes.
"""

from .permissions import (
    check_permission,
    filter_by_user_data,
    has_permission,
    can_user_comment_entrega,
    get_user_permissions,
    PERMISSIONS
)

__all__ = [
    'check_permission',
    'filter_by_user_data',
    'has_permission',
    'can_user_comment_entrega',
    'get_user_permissions',
    'PERMISSIONS',
]