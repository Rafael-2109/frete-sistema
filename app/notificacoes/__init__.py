#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULO DE NOTIFICACOES
Sistema centralizado de notificacoes por email, webhook e in-app

Este modulo implementa:
- AlertaNotificacao: modelo persistente para auditoria
- NotificationDispatcher: dispatcher para email/webhook/in-app
- API endpoints para consulta de notificacoes
"""

from flask import Blueprint

# Blueprint para rotas de notificacao
notificacoes_bp = Blueprint('notificacoes', __name__, url_prefix='/notificacoes')

# Importar rotas (lazy load)
from app.notificacoes import routes  # noqa: E402, F401

# Exportar dispatcher para uso em outros modulos
from app.notificacoes.services import NotificationDispatcher  # noqa: E402, F401
from app.notificacoes.models import AlertaNotificacao  # noqa: E402, F401

__all__ = ['notificacoes_bp', 'NotificationDispatcher', 'AlertaNotificacao']
