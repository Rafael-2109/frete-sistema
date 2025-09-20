#!/usr/bin/env python3
"""
Script para inicializar o scheduler de sincronização incremental

Este script configura e inicia o APScheduler para executar a sincronização
incremental da carteira com o Odoo a cada 30 minutos.

Uso:
    python iniciar_scheduler_incremental.py

Autor: Sistema de Fretes
Data: 2025-01-19
"""

import logging
import signal
import sys
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app import create_app
from app.scheduler.jobs.sincronizacao_incremental import registrar_job, SincronizacaoIncrementalJob

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchedulerManager:
    """Gerenciador do scheduler com tratamento de sinais"""

    def __init__(self):
        self.scheduler = None
        self.app = None
        self.running = False

    def inicializar(self):
        """Inicializa o scheduler e a aplicação"""
        logger.info("="*80)
        logger.info("🚀 INICIALIZANDO SCHEDULER DE SINCRONIZAÇÃO INCREMENTAL")
        logger.info("="*80)

        # Criar aplicação Flask
        self.app = create_app()

        # Configurar jobstores e executors
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=self.app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///scheduler.db')
            )
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=2),
            'processpool': ProcessPoolExecutor(max_workers=1)
        }

        job_defaults = {
            'coalesce': True,  # Combinar execuções perdidas
            'max_instances': 1,  # Uma instância por vez
            'misfire_grace_time': 300  # 5 minutos de tolerância
        }

        # Criar scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='America/Sao_Paulo'
        )

        # Adicionar listeners para eventos
        self.scheduler.add_listener(
            self._job_executed,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error,
            EVENT_JOB_ERROR
        )

        # Registrar o job de sincronização
        with self.app.app_context():
            registrar_job(self.scheduler)

        # Registrar handlers de sinal
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("✅ Scheduler configurado com sucesso")

    def iniciar(self):
        """Inicia o scheduler"""
        try:
            self.scheduler.start()
            self.running = True

            logger.info("✅ Scheduler iniciado")
            logger.info("📋 Jobs agendados:")

            for job in self.scheduler.get_jobs():
                logger.info(f"   - {job.id}: {job.name}")
                logger.info(f"     Próxima execução: {job.next_run_time}")

            logger.info("\n⏰ Aguardando execuções...")
            logger.info("   Pressione Ctrl+C para parar\n")

            # Manter o processo rodando
            while self.running:
                time.sleep(1)

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar scheduler: {e}")
            raise

    def parar(self):
        """Para o scheduler graciosamente"""
        if self.scheduler and self.scheduler.running:
            logger.info("\n🛑 Parando scheduler...")

            # Aguardar jobs em execução
            jobs_running = [j for j in self.scheduler.get_jobs() if j.pending]
            if jobs_running:
                logger.info(f"⏳ Aguardando {len(jobs_running)} jobs terminarem...")

            self.scheduler.shutdown(wait=True)
            self.running = False

            logger.info("✅ Scheduler parado com sucesso")

    def _signal_handler(self, signum, frame):
        """Trata sinais do sistema (Ctrl+C, kill, etc)"""
        logger.info(f"\n📡 Sinal {signum} recebido")
        self.parar()
        sys.exit(0)

    def _job_executed(self, event):
        """Callback quando um job é executado com sucesso"""
        logger.info(f"✅ Job '{event.job_id}' executado com sucesso")

    def _job_error(self, event):
        """Callback quando um job falha"""
        logger.error(f"❌ Job '{event.job_id}' falhou: {event.exception}")

    def executar_agora(self):
        """Executa a sincronização imediatamente (para testes)"""
        logger.info("\n🔧 Executando sincronização manualmente...")

        with self.app.app_context():
            resultado = SincronizacaoIncrementalJob.executar_manualmente()

            if resultado.get('sucesso'):
                logger.info("✅ Execução manual concluída com sucesso")
            else:
                logger.error(f"❌ Execução manual falhou: {resultado.get('erro')}")

            return resultado


def main():
    """Função principal"""
    manager = SchedulerManager()

    try:
        # Inicializar
        manager.inicializar()

        # Perguntar se quer executar agora
        if len(sys.argv) > 1 and sys.argv[1] == '--executar-agora':
            manager.executar_agora()

        # Iniciar scheduler
        manager.iniciar()

    except KeyboardInterrupt:
        logger.info("\n👋 Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.parar()


if __name__ == "__main__":
    main()