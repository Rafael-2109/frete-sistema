#!/usr/bin/env python3
"""
Scheduler com Retry e Reconexão LOCAL (não afeta outras partes do sistema)
==========================================================================
Resolve problema de SSL sem modificar configurações globais
"""

import logging
import signal
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from time import sleep

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configurações
INTERVALO_MINUTOS = 30
JANELA_MINUTOS = 40
STATUS_MINUTOS = 1560
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos


def executar_com_retry():
    """Executa sincronização com retry automático em caso de erro SSL"""

    from app import create_app, db
    from app.odoo.services.carteira_service import CarteiraService
    from app.odoo.services.faturamento_service import FaturamentoService

    logger.info("=" * 60)
    logger.info(f"🔄 SINCRONIZAÇÃO INCREMENTAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    app = create_app()

    with app.app_context():
        # 1️⃣ FATURAMENTO
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"💰 Sincronizando Faturamento (tentativa {tentativa}/{MAX_RETRIES})...")

                # Limpar conexão antes de tentar
                if tentativa > 1:
                    try:
                        db.session.rollback()
                        db.session.remove()
                        sleep(RETRY_DELAY)
                    except:
                        pass

                faturamento_service = FaturamentoService()
                resultado_faturamento = faturamento_service.sincronizar_faturamento_incremental(
                    minutos_janela=JANELA_MINUTOS,
                    primeira_execucao=False,
                    minutos_status=STATUS_MINUTOS
                )

                if resultado_faturamento.get("sucesso"):
                    logger.info("✅ Faturamento sincronizado")
                    logger.info(f"   - Novos: {resultado_faturamento.get('registros_novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_faturamento.get('registros_atualizados', 0)}")
                    break  # Sucesso, sair do loop
                else:
                    logger.error(f"❌ Erro Faturamento: {resultado_faturamento.get('erro')}")

            except Exception as e:
                erro_str = str(e)
                if "SSL" in erro_str or "connection" in erro_str.lower():
                    logger.warning(f"⚠️ Erro de conexão (tentativa {tentativa}/{MAX_RETRIES}): {e}")
                    if tentativa == MAX_RETRIES:
                        logger.error("❌ Faturamento falhou após todas as tentativas")
                else:
                    logger.error(f"❌ Erro não relacionado a conexão: {e}")
                    break

        # Limpar conexões antes da Carteira
        try:
            db.session.remove()
        except:
            pass

        # 2️⃣ CARTEIRA - Com retry específico para problemas de SSL
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📦 Sincronizando Carteira (tentativa {tentativa}/{MAX_RETRIES})...")

                # Limpar conexão antes de cada tentativa
                if tentativa > 1:
                    try:
                        db.session.rollback()
                        db.session.remove()
                        sleep(RETRY_DELAY * tentativa)  # Delay progressivo
                    except:
                        pass

                carteira_service = CarteiraService()

                # Se falhou antes, tentar com janela menor
                janela_atual = JANELA_MINUTOS if tentativa == 1 else 20

                resultado_carteira = carteira_service.sincronizar_incremental(
                    minutos_janela=janela_atual,
                    primeira_execucao=False
                )

                if resultado_carteira.get("sucesso"):
                    logger.info("✅ Carteira sincronizada")
                    logger.info(f"   - Pedidos: {resultado_carteira.get('pedidos_processados', 0)}")
                    logger.info(f"   - Atualizados: {resultado_carteira.get('itens_atualizados', 0)}")
                    break  # Sucesso!
                else:
                    logger.error(f"❌ Erro Carteira: {resultado_carteira.get('erro')}")

            except Exception as e:
                erro_str = str(e)
                if "SSL" in erro_str or "connection" in erro_str.lower():
                    logger.warning(f"⚠️ Erro SSL na Carteira (tentativa {tentativa}/{MAX_RETRIES})")

                    if tentativa == MAX_RETRIES:
                        logger.error("❌ Carteira falhou após todas as tentativas")
                        logger.error(f"   Erro final: {e}")
                else:
                    logger.error(f"❌ Erro não relacionado a conexão: {e}")
                    break

        # Limpar ao final
        try:
            db.session.remove()
        except:
            pass


def executar_inicial():
    """Execução inicial com janela maior e mais retries"""
    logger.info("🚀 SINCRONIZAÇÃO INICIAL (120 minutos)")

    global JANELA_MINUTOS, MAX_RETRIES
    janela_original = JANELA_MINUTOS
    retries_original = MAX_RETRIES

    JANELA_MINUTOS = 120
    MAX_RETRIES = 5  # Mais retries na primeira execução

    try:
        executar_com_retry()
    finally:
        JANELA_MINUTOS = janela_original
        MAX_RETRIES = retries_original


def main():
    """Função principal"""
    logger.info("🎯 INICIANDO SCHEDULER COM RETRY")

    # Executar inicial
    executar_inicial()

    # Configurar scheduler
    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")

    scheduler.add_job(
        func=executar_com_retry,
        trigger="interval",
        minutes=INTERVALO_MINUTOS,
        id="sincronizacao_com_retry",
        name="Sincronização com Retry",
        max_instances=1,  # Apenas uma execução por vez
        misfire_grace_time=300
    )

    logger.info(f"✅ Scheduler configurado - execução a cada {INTERVALO_MINUTOS} minutos")
    logger.info(f"   - Retry automático: {MAX_RETRIES} tentativas")
    logger.info(f"   - Delay entre tentativas: {RETRY_DELAY} segundos")

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