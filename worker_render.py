#!/usr/bin/env python3
"""
Worker otimizado para o Render - Evita importações circulares
Versão segura para executar jobs assíncronos no ambiente de produção
"""

import os
import sys
import logging
import threading
import time
from redis import Redis
from rq import Worker, Queue, Connection
from datetime import datetime
import click

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_redis_connection():
    """Configura conexão com Redis"""
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    logger.info(f"Conectando ao Redis: {redis_url[:30]}...")
    return Redis.from_url(redis_url)

def worker_startup():
    """Executa ao iniciar o worker"""
    logger.info("="*60)
    logger.info("🚀 WORKER RENDER - INICIANDO")
    logger.info(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔧 PID: {os.getpid()}")
    logger.info(f"🌍 Ambiente: RENDER")
    logger.info("="*60)

def worker_shutdown():
    """Executa ao parar o worker"""
    logger.info("="*60)
    logger.info("🛑 WORKER RENDER - ENCERRANDO")
    logger.info(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

def run_sendas_scheduler():
    """
    Thread separada para o scheduler Sendas
    Executa a cada 20 minutos verificando a fila
    """
    logger.info("🚀 [Scheduler Sendas] Iniciado em thread separada")

    # Aguardar 2 minutos antes da primeira execução
    logger.info("⏳ [Scheduler Sendas] Aguardando 2 minutos antes da primeira verificação...")
    time.sleep(120)

    while True:
        try:
            logger.info(f"⏰ [Scheduler Sendas] Verificando fila - {datetime.now().strftime('%H:%M:%S')}")

            # Importações lazy apenas quando necessário
            from app import create_app
            from app.portal.workers.sendas_fila_scheduler import processar_fila_sendas_scheduled

            # Executar com contexto da aplicação
            app = create_app()
            with app.app_context():
                resultado = processar_fila_sendas_scheduled()

                if resultado['success']:
                    if resultado['total_processado'] > 0:
                        logger.info(f"✅ [Scheduler Sendas] {resultado['message']}")
                    else:
                        logger.debug("📭 [Scheduler Sendas] Fila vazia")
                else:
                    logger.error(f"❌ [Scheduler Sendas] Erro: {resultado['message']}")

            # Aguardar 20 minutos
            logger.info("⏳ [Scheduler Sendas] Aguardando 20 minutos para próxima verificação...")
            time.sleep(20 * 60)  # 20 minutos

        except Exception as e:
            logger.error(f"❌ Erro no scheduler Sendas: {e}")
            logger.info("⏳ [Scheduler Sendas] Aguardando 5 minutos antes de tentar novamente...")
            time.sleep(5 * 60)  # 5 minutos em caso de erro

def run_single_worker(config, burst=False):
    """Executa um worker individual"""
    import random
    worker_name = f'render-worker-{os.getpid()}-{int(time.time())}-{random.randint(1000, 9999)}'

    worker = Worker(
        name=worker_name,
        queues=config['queues'],
        connection=config['connection'],
        log_job_description=True,
        default_worker_ttl=1800,  # 30 minutos TTL para o worker
        default_result_ttl=86400,  # 24 horas para resultados
        job_monitoring_interval=30  # Monitorar jobs a cada 30 segundos
    )

    # Estatísticas iniciais
    for queue in config['queues']:
        job_count = len(queue)
        if job_count > 0:
            logger.info(f"📦 Fila '{queue.name}': {job_count} jobs pendentes")

    # Executar worker
    logger.info(f"👷 Worker '{worker_name}' processando jobs...")

    if burst:
        logger.info("💨 Modo BURST ativado - processará jobs existentes e parará")
        worker.work(burst=True, logging_level=config['log_level'])
    else:
        logger.info("♾️  Modo CONTÍNUO - aguardando novos jobs...")
        worker.work(
            logging_level=config['log_level'],
            with_scheduler=False  # Desabilitar scheduler interno do RQ
        )

@click.command()
@click.option('--workers', default=2, help='Número de workers paralelos')
@click.option('--verbose', is_flag=True, help='Modo verbose com mais logs')
@click.option('--burst', is_flag=True, help='Executa jobs pendentes e para')
@click.option('--queues', default='atacadao,sendas,high,default', help='Filas a processar')
def run_worker(workers, verbose, burst, queues):
    """
    Executa o worker otimizado para o Render
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Modo verbose ativado")

    # Configurar conexão
    redis_conn = setup_redis_connection()

    # Parsear filas
    queue_names = [q.strip() for q in queues.split(',')]
    logger.info(f"📋 Filas monitoradas: {queue_names}")

    # Criar objetos Queue
    queues_obj = [Queue(name, connection=redis_conn) for name in queue_names]

    # Configurações do worker
    worker_config = {
        'connection': redis_conn,
        'queues': queues_obj,
        'log_level': 'DEBUG' if verbose else 'INFO'
    }

    # Verificar e iniciar scheduler Sendas
    enable_scheduler = os.environ.get('ENABLE_SENDAS_SCHEDULER', 'true').lower() == 'true'

    if enable_scheduler:
        scheduler_thread = threading.Thread(
            target=run_sendas_scheduler,
            daemon=True,
            name='SendasScheduler'
        )
        scheduler_thread.start()
        logger.info("✅ [Scheduler Sendas] HABILITADO - verificação a cada 20 minutos")
    else:
        logger.warning("⚠️ [Scheduler Sendas] DESABILITADO")

    try:
        with Connection(redis_conn):
            # Startup
            worker_startup()

            if workers > 1:
                logger.info(f"🔄 Iniciando {workers} workers paralelos...")

                from multiprocessing import Process

                processes = []
                for i in range(workers):
                    p = Process(target=run_single_worker, args=(worker_config, burst))
                    p.start()
                    processes.append(p)
                    logger.info(f"   Worker {i+1} iniciado (PID: {p.pid})")

                # Aguardar todos terminarem
                for p in processes:
                    p.join()
            else:
                # Worker único
                run_single_worker(worker_config, burst)

            # Shutdown
            worker_shutdown()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrompido pelo usuário (Ctrl+C)")
        worker_shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Erro fatal no worker: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_worker()