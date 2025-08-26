"""
Workers para processamento assíncrono com Redis Queue
"""

from redis import Redis
from rq import Queue
from flask import current_app
import os
import logging

logger = logging.getLogger(__name__)

def get_redis_connection():
    """Obtém conexão com Redis"""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return Redis.from_url(redis_url)

def get_queue(queue_name='default'):
    """Obtém uma fila específica do Redis Queue"""
    redis_conn = get_redis_connection()
    return Queue(queue_name, connection=redis_conn)

def enqueue_job(func, *args, queue_name='default', timeout='30m', **kwargs):
    """
    Enfileira um job para execução assíncrona
    
    Args:
        func: Função a ser executada
        *args: Argumentos posicionais
        queue_name: Nome da fila (default, high, low, atacadao)
        timeout: Timeout do job (padrão 30 minutos)
        **kwargs: Argumentos nomeados
    
    Returns:
        Job object com ID e status
    """
    try:
        queue = get_queue(queue_name)
        job = queue.enqueue(
            func,
            *args,
            **kwargs,
            job_timeout=timeout,
            result_ttl=86400,  # Mantém resultado por 24 horas
            failure_ttl=86400  # Mantém falhas por 24 horas
        )
        logger.info(f"Job {job.id} enfileirado na fila '{queue_name}'")
        return job
    except Exception as e:
        logger.error(f"Erro ao enfileirar job: {e}")
        raise