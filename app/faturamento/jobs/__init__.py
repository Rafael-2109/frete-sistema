"""
Jobs para processamento assincrono de faturamento
Usa Redis Queue (RQ) na fila 'faturamento'
"""

from app.portal.workers import enqueue_job, get_queue, get_redis_connection

__all__ = ['enqueue_job', 'get_queue', 'get_redis_connection']
