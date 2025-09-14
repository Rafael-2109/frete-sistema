#!/usr/bin/env python3
"""
Script para iniciar workers do Redis Queue
Para processamento assíncrono de ruptura e outros jobs
"""

import os
import sys
from rq import Worker, Connection
from redis import Redis
import logging
import multiprocessing
import threading
import time
from datetime import datetime

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
from app.portal.workers.sendas_fila_scheduler import processar_fila_sendas_scheduled

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

def run_sendas_scheduler():
    """
    Thread separada para o scheduler Sendas
    Executa a cada 20 minutos
    """
    logger.info("🚀 Scheduler Sendas iniciado em thread separada")

    # Aguardar 1 minuto antes da primeira execução para dar tempo dos workers iniciarem
    time.sleep(60)

    while True:
        try:
            logger.info(f"⏰ [Scheduler Sendas] Verificando fila - {datetime.now().strftime('%H:%M:%S')}")

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
            time.sleep(5 * 60)  # 5 minutos em caso de erro

def main():
    """Função principal"""
    # Configurações
    NUM_WORKERS = int(os.environ.get('NUM_WORKERS', 3))  # Aumentado para 3 workers
    QUEUES = ['default', 'high', 'low', 'atacadao', 'sendas']  # Adicionado 'sendas'
    ENABLE_SENDAS_SCHEDULER = os.environ.get('ENABLE_SENDAS_SCHEDULER', 'true').lower() == 'true'

    logger.info(f"Iniciando {NUM_WORKERS} workers para filas: {QUEUES}")

    # Iniciar scheduler Sendas em thread separada (se habilitado)
    if ENABLE_SENDAS_SCHEDULER:
        scheduler_thread = threading.Thread(
            target=run_sendas_scheduler,
            daemon=True,
            name='SendasScheduler'
        )
        scheduler_thread.start()
        logger.info("✅ Scheduler Sendas habilitado - verificação a cada 20 minutos")
    else:
        logger.info("⚠️ Scheduler Sendas desabilitado (ENABLE_SENDAS_SCHEDULER=false)")
    
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