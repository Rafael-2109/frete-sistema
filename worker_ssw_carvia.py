#!/usr/bin/env python3
"""
Worker dedicado para emissao automatica de CTe SSW (CarVia)
Executa jobs Playwright (headless Chromium) que duram 60-120s.

Uso:
    python worker_ssw_carvia.py
    python worker_ssw_carvia.py --verbose
    python worker_ssw_carvia.py --burst  # executa pendentes e para

Requer:
    - Redis (REDIS_URL no .env)
    - Playwright + Chromium instalados
    - Credenciais SSW (SSW_URL, SSW_DOMINIO, SSW_CPF, SSW_LOGIN, SSW_SENHA)
"""

import os
import sys
import re
import logging
from redis import Redis
from rq import Worker, Queue
import click

# Adicionar o diretorio do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.utils.timezone import agora_utc_naive

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_redis_connection():
    """Configura conexao com Redis."""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    safe_url = re.sub(r'://([^@]+)@', '://***@', redis_url)
    logger.info(f"Conectando ao Redis: {safe_url}")
    return Redis.from_url(redis_url)


def worker_startup():
    """Executa ao iniciar o worker."""
    logger.info("=" * 60)
    logger.info("WORKER SSW CARVIA - INICIANDO")
    logger.info(f"Data/Hora: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"PID: {os.getpid()}")
    logger.info("=" * 60)


def worker_shutdown():
    """Executa ao parar o worker."""
    logger.info("=" * 60)
    logger.info("WORKER SSW CARVIA - ENCERRANDO")
    logger.info(f"Data/Hora: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


def job_success_handler(job, connection, result, *args, **kwargs):
    """Handler para jobs bem-sucedidos."""
    logger.info(f"Job {job.id} concluido com sucesso")
    logger.info(f"  Funcao: {job.func_name}")
    if job.ended_at and job.started_at:
        logger.info(f"  Duracao: {job.ended_at - job.started_at}")
    if result:
        logger.info(f"  Resultado: {str(result)[:200]}")


def job_failure_handler(job, connection, type, value, traceback):
    """Handler para jobs que falharam."""
    logger.error(f"Job {job.id} falhou!")
    logger.error(f"  Funcao: {job.func_name}")
    logger.error(f"  Erro: {type.__name__}: {value}")
    logger.error(f"  Args: {job.args}")


def run_single_worker(config, burst=False):
    """Executa um unico worker."""
    w = Worker(
        config['queues'],
        name=config['name'],
        connection=config['connection'],
    )
    w.work(
        burst=burst,
        logging_level=config.get('log_level', 'INFO'),
    )


@click.command()
@click.option('--verbose', is_flag=True, help='Modo verbose com mais logs')
@click.option('--burst', is_flag=True, help='Executa jobs pendentes e para')
@click.option('--queues', default='ssw_carvia', help='Filas a processar (separadas por virgula)')
def run_worker(verbose, burst, queues):
    """Executa o worker SSW CarVia para emissao automatica de CTe."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Modo verbose ativado")

    redis_conn = setup_redis_connection()

    queue_names = [q.strip() for q in queues.split(',')]
    logger.info(f"Filas monitoradas: {queue_names}")

    queues_obj = [Queue(name, connection=redis_conn) for name in queue_names]

    worker_config = {
        'name': f'ssw-carvia-worker-{os.getpid()}',
        'connection': redis_conn,
        'queues': queues_obj,
        'log_level': 'DEBUG' if verbose else 'INFO',
    }

    try:
        worker_startup()
        run_single_worker(worker_config, burst)
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuario")
    finally:
        worker_shutdown()


if __name__ == '__main__':
    run_worker()
