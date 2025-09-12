#!/usr/bin/env python3
"""
Script para iniciar workers do Redis Queue
Para processamento assíncrono de ruptura e outros jobs
"""

import os
import sys
from rq import Worker, Queue, Connection
from redis import Redis
import logging
import multiprocessing

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar app para contexto
from app import create_app

def start_worker(queue_names):
    """Inicia um worker para as filas especificadas"""
    app = create_app()
    
    with app.app_context():
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_conn = Redis.from_url(redis_url)
        
        try:
            with Connection(redis_conn):
                worker = Worker(queue_names)
                logger.info(f"Worker iniciado para filas: {queue_names}")
                worker.work()
        except Exception as e:
            logger.error(f"Erro no worker: {e}")
            sys.exit(1)

def main():
    """Função principal"""
    # Configurações
    NUM_WORKERS = int(os.environ.get('NUM_WORKERS', 3))  # Aumentado para 3 workers
    QUEUES = ['default', 'high', 'low', 'atacadao', 'sendas']  # Adicionado 'sendas'
    
    logger.info(f"Iniciando {NUM_WORKERS} workers para filas: {QUEUES}")
    
    if NUM_WORKERS > 1:
        # Múltiplos workers em processos separados
        processes = []
        for i in range(NUM_WORKERS):
            p = multiprocessing.Process(
                target=start_worker,
                args=(QUEUES,),
                name=f'Worker-{i+1}'
            )
            p.start()
            processes.append(p)
            logger.info(f"Worker {i+1} iniciado")
        
        # Aguardar todos os processos
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
            for p in processes:
                p.terminate()
            sys.exit(0)
    else:
        # Worker único
        start_worker(QUEUES)

if __name__ == '__main__':
    main()