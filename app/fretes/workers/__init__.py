"""
Workers para processamento assíncrono de lançamentos no Odoo
Usa Redis Queue (RQ) na fila 'odoo_lancamento'
"""

from app.portal.workers import enqueue_job, get_queue, get_redis_connection

__all__ = ['enqueue_job', 'get_queue', 'get_redis_connection']
