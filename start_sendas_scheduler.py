#!/usr/bin/env python3
"""
Script para iniciar o scheduler da fila de agendamento Sendas
Processa a fila a cada 20 minutos se houver itens pendentes
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from threading import Thread

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar função do scheduler
from app.portal.workers.sendas_fila_scheduler import processar_fila_sendas_scheduled

def run_scheduler():
    """
    Executa o scheduler a cada 20 minutos
    """
    logger.info("🚀 Scheduler da Fila Sendas iniciado")
    logger.info("📅 Processamento programado a cada 20 minutos (se houver itens na fila)")
    
    while True:
        try:
            # Executar processamento
            logger.info(f"⏰ Executando verificação da fila - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            resultado = processar_fila_sendas_scheduled()
            
            if resultado['success']:
                if resultado['total_processado'] > 0:
                    logger.info(f"✅ Processamento concluído: {resultado['message']}")
                else:
                    logger.info("📭 Fila vazia - nada processado")
            else:
                logger.error(f"❌ Erro no processamento: {resultado['message']}")
            
            # Aguardar 20 minutos
            logger.info("⏳ Aguardando 20 minutos para próxima verificação...")
            time.sleep(20 * 60)  # 20 minutos em segundos
            
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler interrompido pelo usuário")
            break
        except Exception as e:
            logger.error(f"❌ Erro inesperado no scheduler: {e}")
            logger.info("⏳ Aguardando 5 minutos antes de tentar novamente...")
            time.sleep(5 * 60)  # 5 minutos em caso de erro

def run_with_redis_scheduler():
    """
    Alternativa: Usar RQ Scheduler para agendar jobs
    Requer: pip install rq-scheduler
    """
    try:
        from rq_scheduler import Scheduler
        from redis import Redis
        from rq import Queue
        from datetime import datetime
        
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_conn = Redis.from_url(redis_url)
        
        scheduler = Scheduler(connection=redis_conn)
        
        # Agendar job recorrente
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=processar_fila_sendas_scheduled,
            interval=1200,  # 20 minutos em segundos
            repeat=None,  # Repetir indefinidamente
            queue_name='sendas'
        )
        
        logger.info("✅ Job agendado no RQ Scheduler - execução a cada 20 minutos")
        logger.info("Use 'rqscheduler' para iniciar o scheduler do RQ")
        
    except ImportError:
        logger.warning("rq-scheduler não instalado. Use: pip install rq-scheduler")
        logger.info("Usando scheduler simples com sleep...")
        run_scheduler()

def main():
    """
    Função principal
    """
    # Verificar modo de execução
    use_rq_scheduler = os.environ.get('USE_RQ_SCHEDULER', 'false').lower() == 'true'
    
    if use_rq_scheduler:
        logger.info("Usando RQ Scheduler...")
        run_with_redis_scheduler()
    else:
        logger.info("Usando scheduler simples com sleep...")
        run_scheduler()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n🛑 Scheduler finalizado")
        sys.exit(0)