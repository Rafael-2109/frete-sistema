#!/usr/bin/env python3
"""
Worker dedicado para processar agendamentos do Atacadão
Executa jobs assíncronos via Redis Queue

Uso:
    python worker_atacadao.py
    
    # Ou para múltiplos workers:
    python worker_atacadao.py --workers 2
    
    # Para modo verbose:
    python worker_atacadao.py --verbose
"""

import os
import sys
import logging
import time
from redis import Redis
from rq import Worker, Queue
from rq.job import Job
import click
from app.utils.timezone import agora_utc_naive

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
    logger.info("🚀 WORKER ATACADÃO - INICIANDO")
    logger.info(f"📅 Data/Hora: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🔧 PID: {os.getpid()}")
    logger.info("="*60)

def worker_shutdown():
    """Executa ao parar o worker"""
    logger.info("="*60)
    logger.info("🛑 WORKER ATACADÃO - ENCERRANDO")
    logger.info(f"📅 Data/Hora: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

# ✅ REMOVIDO Nov/2025: Função run_sendas_scheduler() - automação Playwright descontinuada
# O processamento agora é feito manualmente via exportação de planilha


def job_success_handler(job, connection, result, *args, **kwargs):
    """Handler para jobs bem-sucedidos"""
    logger.info(f"✅ Job {job.id} concluído com sucesso")
    logger.info(f"   Função: {job.func_name}")
    logger.info(f"   Duração: {job.ended_at - job.started_at if job.ended_at and job.started_at else 'N/A'}")
    if result:
        logger.info(f"   Resultado: {str(result)[:200]}...")

def job_failure_handler(job, connection, type, value, traceback):
    """Handler para jobs que falharam"""
    logger.error(f"❌ Job {job.id} falhou!")
    logger.error(f"   Função: {job.func_name}")
    logger.error(f"   Erro: {type.__name__}: {value}")
    logger.error(f"   Args: {job.args}")
    logger.error(f"   Kwargs: {job.kwargs}")

@click.command()
@click.option('--workers', default=1, help='Número de workers paralelos')
@click.option('--verbose', is_flag=True, help='Modo verbose com mais logs')
@click.option('--burst', is_flag=True, help='Executa jobs pendentes e para')
@click.option('--queues', default='atacadao,high,default', help='Filas a processar (separadas por vírgula)')
def run_worker(workers, verbose, burst, queues):
    """
    Executa o worker do Atacadão
    
    Args:
        workers: Número de workers paralelos
        verbose: Ativa logs detalhados
        burst: Modo burst (executa e para)
        queues: Filas a processar
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
        'name': f'atacadao-worker-{os.getpid()}',
        'connection': redis_conn,
        'queues': queues_obj,
        'log_level': 'DEBUG' if verbose else 'INFO',
        'log_format': '%(asctime)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S'
    }
    
    # ✅ REMOVIDO Nov/2025: Scheduler Sendas - automação Playwright descontinuada
    # O processamento agora é feito manualmente via exportação de planilha
    logger.info("ℹ️ [Scheduler Sendas] REMOVIDO - usar exportação manual em /portal/sendas/exportacao")

    try:
        # Startup
        worker_startup()

        if workers > 1:
            logger.info(f"🔄 Iniciando {workers} workers paralelos...")

            # Importar multiprocessing
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

def run_single_worker(config, burst=False):
    """Executa um worker individual"""
    # Usar PID do processo atual + timestamp + random para garantir nome único
    import random
    worker_name = f'atacadao-worker-{os.getpid()}-{int(time.time())}-{random.randint(1000, 9999)}'
    
    worker = Worker(
        name=worker_name,
        queues=config['queues'],
        connection=config['connection'],
        log_job_description=True
    )
    
    # Estatísticas iniciais
    for queue in config['queues']:
        job_count = len(queue)
        if job_count > 0:
            logger.info(f"📦 Fila '{queue.name}': {job_count} jobs pendentes")
    
    # Executar worker
    logger.info(f"👷 Worker '{config['name']}' processando jobs...")
    
    if burst:
        logger.info("💨 Modo BURST ativado - processará jobs existentes e parará")
        worker.work(burst=True, logging_level=config['log_level'])
    else:
        logger.info("♾️  Modo CONTÍNUO - aguardando novos jobs...")
        worker.work(logging_level=config['log_level'])

def check_status():
    """Verifica status das filas e jobs"""
    redis_conn = setup_redis_connection()
    
    print("\n" + "="*60)
    print("📊 STATUS DAS FILAS - ATACADÃO")
    print("="*60)
    
    queue_names = ['atacadao', 'high', 'default', 'low']
    
    for queue_name in queue_names:
        queue = Queue(queue_name, connection=redis_conn)
        
        # Jobs pendentes
        pending_count = len(queue)
        
        # Jobs em execução
        started_registry = queue.started_job_registry
        started_count = len(started_registry)
        
        # Jobs concluídos
        finished_registry = queue.finished_job_registry
        finished_count = len(finished_registry)
        
        # Jobs falhados
        failed_registry = queue.failed_job_registry
        failed_count = len(failed_registry)
        
        print(f"\n📋 Fila: {queue_name}")
        print(f"   ⏳ Pendentes: {pending_count}")
        print(f"   🔄 Em execução: {started_count}")
        print(f"   ✅ Concluídos: {finished_count}")
        print(f"   ❌ Falhados: {failed_count}")
        
        # Mostrar jobs pendentes
        if pending_count > 0 and pending_count <= 5:
            print(f"   📦 Jobs pendentes:")
            for job_id in queue.job_ids[:5]:
                job = Job.fetch(job_id, connection=redis_conn)
                print(f"      - {job.func_name} (ID: {job.id[:8]}...)")
    
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    # Se executado com --status, mostra status
    if '--status' in sys.argv:
        check_status()
    else:
        # Executar worker normalmente
        run_worker()