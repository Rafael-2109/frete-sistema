#!/usr/bin/env python3
"""
Scheduler Resiliente com Reconexão Automática
=============================================
Resolve problema de SSL connection closed no PostgreSQL
"""

import logging
import signal
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configurações
INTERVALO_MINUTOS = 30
JANELA_MINUTOS = 40
STATUS_MINUTOS = 1560


def executar_com_reconexao():
    """Executa sincronização com reconexão automática ao banco"""

    from app import create_app, db
    from app.odoo.services.carteira_service import CarteiraService
    from app.odoo.services.faturamento_service import FaturamentoService

    try:
        logger.info("=" * 60)
        logger.info(f"🔄 SINCRONIZAÇÃO INCREMENTAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        app = create_app()

        with app.app_context():
            # IMPORTANTE: Forçar nova conexão antes de cada sincronização
            try:
                db.session.close()
                db.engine.dispose()
                logger.info("♻️ Conexões antigas fechadas")
            except:
                pass

            # 1️⃣ FATURAMENTO com proteção
            try:
                logger.info("💰 Sincronizando Faturamento...")
                faturamento_service = FaturamentoService()

                # Criar nova sessão para faturamento
                resultado_faturamento = faturamento_service.sincronizar_faturamento_incremental(
                    minutos_janela=JANELA_MINUTOS,
                    primeira_execucao=False,
                    minutos_status=STATUS_MINUTOS
                )

                if resultado_faturamento.get("sucesso"):
                    logger.info("✅ Faturamento sincronizado")
                    logger.info(f"   - Novos: {resultado_faturamento.get('registros_novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_faturamento.get('registros_atualizados', 0)}")
                else:
                    logger.error(f"❌ Erro Faturamento: {resultado_faturamento.get('erro')}")

                # Commit e limpar
                db.session.commit()
                db.session.remove()

            except Exception as e:
                logger.error(f"❌ Erro fatal Faturamento: {e}")
                db.session.rollback()
                db.session.remove()

            # RECONECTAR antes da Carteira
            try:
                db.engine.dispose()
                logger.info("♻️ Reconexão antes da Carteira")
            except:
                pass

            # 2️⃣ CARTEIRA com proteção extra
            try:
                logger.info("📦 Sincronizando Carteira...")

                # IMPORTANTE: Criar nova instância com nova conexão
                carteira_service = CarteiraService()

                # Executar em blocos menores se necessário
                resultado_carteira = carteira_service.sincronizar_incremental(
                    minutos_janela=JANELA_MINUTOS,
                    primeira_execucao=False
                )

                if resultado_carteira.get("sucesso"):
                    logger.info("✅ Carteira sincronizada")
                    logger.info(f"   - Pedidos: {resultado_carteira.get('pedidos_processados', 0)}")
                    logger.info(f"   - Atualizados: {resultado_carteira.get('itens_atualizados', 0)}")
                else:
                    logger.error(f"❌ Erro Carteira: {resultado_carteira.get('erro')}")

                # Commit final
                db.session.commit()

            except Exception as e:
                logger.error(f"❌ Erro fatal Carteira: {e}")

                # Tentar reconectar e executar novamente
                if "SSL" in str(e) or "connection" in str(e).lower():
                    logger.info("🔄 Tentando reconectar...")
                    try:
                        db.session.rollback()
                        db.session.remove()
                        db.engine.dispose()

                        # Segunda tentativa com nova conexão
                        carteira_service = CarteiraService()
                        resultado = carteira_service.sincronizar_incremental(JANELA_MINUTOS, False)

                        if resultado.get("sucesso"):
                            logger.info("✅ Carteira sincronizada na segunda tentativa")

                    except Exception as e2:
                        logger.error(f"❌ Falha mesmo após reconexão: {e2}")

            finally:
                # Sempre limpar conexões
                try:
                    db.session.remove()
                    db.engine.dispose()
                except:
                    pass

    except Exception as e:
        logger.error(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()


def executar_inicial():
    """Execução inicial com janela maior"""
    logger.info("🚀 SINCRONIZAÇÃO INICIAL (120 minutos)")

    global JANELA_MINUTOS
    janela_original = JANELA_MINUTOS
    JANELA_MINUTOS = 120

    try:
        executar_com_reconexao()
    finally:
        JANELA_MINUTOS = janela_original


def main():
    """Função principal com scheduler resiliente"""
    logger.info("🎯 INICIANDO SCHEDULER RESILIENTE")

    # Executar inicial
    executar_inicial()

    # Configurar scheduler
    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")

    scheduler.add_job(
        func=executar_com_reconexao,
        trigger="interval",
        minutes=INTERVALO_MINUTOS,
        id="sincronizacao_resiliente",
        name="Sincronização Resiliente",
        max_instances=1,
        misfire_grace_time=300
    )

    logger.info(f"✅ Scheduler configurado - execução a cada {INTERVALO_MINUTOS} minutos")

    # Shutdown handler
    def shutdown(signum, frame):
        logger.info("🛑 Encerrando scheduler...")
        scheduler.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Scheduler encerrado")


if __name__ == "__main__":
    main()