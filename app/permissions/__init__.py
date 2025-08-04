"""
Sistema de Permissões Simples
==============================

Sistema minimalista mas funcional para controle de acesso.
"""

from flask import Blueprint


# Importar rotas DEPOIS de criar o blueprint
from . import routes

# Importar funções de permissão
from .permissions import (
    check_permission,
    filter_by_user_data,
    has_permission,
    can_user_comment_entrega,
    get_user_permissions,
    PERMISSIONS
)
# Criar blueprint para permissões PRIMEIRO



__all__ = [
    'check_permission', 
    'filter_by_user_data',
    'has_permission',
    'can_user_comment_entrega',
    'get_user_permissions',
    'PERMISSIONS',
]