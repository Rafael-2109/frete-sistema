# -*- coding: utf-8 -*-
"""
Workers para processamento assincrono de baixas de titulos
==========================================================

Utiliza o sistema RQ (Redis Queue) existente.
"""

# Re-exportar funcoes do portal.workers para conveniencia
from app.portal.workers import enqueue_job, get_queue, get_redis_connection

__all__ = ['enqueue_job', 'get_queue', 'get_redis_connection']
