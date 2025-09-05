#!/usr/bin/env python3
"""
Script para iniciar 2 workers de ruptura localmente
Pode ser executado tanto local quanto em produção
"""
import os
import sys
import multiprocessing
from redis import Redis
from rq import Worker, Queue
import logging

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_worker(worker_name, queue_name):
    """Inicia um worker individual"""
    try:
        # Conectar ao Redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_conn = Redis.from_url(redis_url)
        
        # Criar fila
        queue = Queue(queue_name, connection=redis_conn)
        
        # Criar worker
        worker = Worker(
            [queue],
            connection=redis_conn,
            name=worker_name
        )
        
        logger.info(f"🚀 Worker {worker_name} iniciado para fila: {queue_name}")
        logger.info(f"   Redis URL: {redis_url}")
        logger.info(f"   Aguardando jobs...")
        
        # Iniciar trabalho
        worker.work()
        
    except KeyboardInterrupt:
        logger.info(f"⏹️ Worker {worker_name} interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro no worker {worker_name}: {e}")
        sys.exit(1)

def main():
    """Função principal"""
    logger.info("="*60)
    logger.info("🔧 SISTEMA DE WORKERS DE RUPTURA")
    logger.info("="*60)
    
    # Verificar conexão Redis
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_conn = Redis.from_url(redis_url)
        redis_conn.ping()
        logger.info(f"✅ Redis conectado: {redis_url}")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar no Redis: {e}")
        logger.error("   Certifique-se que o Redis está rodando:")
        logger.error("   - Local: redis-server")
        logger.error("   - Docker: docker run -d -p 6379:6379 redis")
        sys.exit(1)
    
    # Criar processos para os workers
    workers = [
        multiprocessing.Process(
            target=start_worker,
            args=(f'ruptura-worker-1', 'ruptura_worker1'),
            daemon=True
        ),
        multiprocessing.Process(
            target=start_worker,
            args=(f'ruptura-worker-2', 'ruptura_worker2'),
            daemon=True
        )
    ]
    
    # Iniciar workers
    logger.info("🚀 Iniciando 2 workers de ruptura...")
    for worker in workers:
        worker.start()
    
    logger.info("✅ Workers iniciados com sucesso!")
    logger.info("   Pressione Ctrl+C para parar")
    logger.info("-"*60)
    
    try:
        # Aguardar workers
        for worker in workers:
            worker.join()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Parando workers...")
        for worker in workers:
            worker.terminate()
            worker.join(timeout=5)
        logger.info("✅ Workers parados com sucesso")

if __name__ == "__main__":
    main()