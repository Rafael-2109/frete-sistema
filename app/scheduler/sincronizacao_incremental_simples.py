#!/usr/bin/env python3
"""
Scheduler Simplificado para Sincronização Incremental
=====================================================

Estratégia simples e eficaz:
1. Executa sincronização IMEDIATAMENTE ao iniciar (recupera dados do deploy)
2. Agenda execuções a cada 30 minutos
3. Busca sempre os últimos 40 minutos (sobreposição de 10 min)

Autor: Sistema de Fretes
"""

import logging
import signal
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from app import create_app
from app.odoo.services.carteira_service import CarteiraService
from app.odoo.services.faturamento_service import FaturamentoService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configurações
INTERVALO_MINUTOS = 30  # Executa a cada 30 minutos
JANELA_MINUTOS = 40  # Busca últimos 40 minutos
STATUS_MINUTOS = 1560  # Busca status das últimas 26 horas (26*60)


def executar_sincronizacao():
    """Executa a sincronização incremental de Carteira e Faturamento"""
    try:
        logger.info("=" * 60)
        logger.info(f"🔄 SINCRONIZAÇÃO INCREMENTAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📊 Buscando alterações dos últimos {JANELA_MINUTOS} minutos")
        logger.info("=" * 60)

        app = create_app()
        with app.app_context():
            # 1️⃣ SINCRONIZAR FATURAMENTO PRIMEIRO (ordem segura)
            logger.info("💰 Sincronizando Faturamento...")
            faturamento_service = FaturamentoService()
            resultado_faturamento = faturamento_service.sincronizar_faturamento_incremental(
                minutos_janela=JANELA_MINUTOS,
                primeira_execucao=False,
                minutos_status=STATUS_MINUTOS
            )

            if resultado_faturamento.get("sucesso"):
                logger.info("✅ Faturamento sincronizado com sucesso")
                logger.info(f"   - Novos: {resultado_faturamento.get('registros_novos', 0)}")
                logger.info(f"   - Atualizados: {resultado_faturamento.get('registros_atualizados', 0)}")
                logger.info(f"   - Tempo: {resultado_faturamento.get('tempo_execucao', 0):.2f}s")

                # Mostrar estatísticas extras se disponíveis
                sincronizacoes = resultado_faturamento.get("sincronizacoes", {})
                if sincronizacoes:
                    logger.info(f"   - Entregas: {sincronizacoes.get('entregas_sincronizadas', 0)}")
                    logger.info(f"   - Fretes: {sincronizacoes.get('fretes_lancados', 0)}")
            else:
                logger.error(f"❌ Erro no Faturamento: {resultado_faturamento.get('erro')}")

            # 2️⃣ SINCRONIZAR CARTEIRA DEPOIS (após faturamento protegido)
            logger.info("📦 Sincronizando Carteira...")
            carteira_service = CarteiraService()
            resultado_carteira = carteira_service.sincronizar_incremental(
                minutos_janela=JANELA_MINUTOS, primeira_execucao=False
            )

            if resultado_carteira.get("sucesso"):
                logger.info("✅ Carteira sincronizada com sucesso")
                logger.info(f"   - Pedidos: {resultado_carteira.get('pedidos_processados', 0)}")
                logger.info(f"   - Atualizados: {resultado_carteira.get('itens_atualizados', 0)}")
                logger.info(f"   - Tempo: {resultado_carteira.get('tempo_execucao', 0):.2f}s")
            else:
                logger.error(f"❌ Erro na Carteira: {resultado_carteira.get('erro')}")

    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback

        traceback.print_exc()


def executar_sincronizacao_inicial():
    """Executa sincronização com janela maior após deploy (Carteira e Faturamento)"""
    try:
        # Usar janela de 2 horas na primeira execução (cobre qualquer deploy)
        janela_inicial = 120

        logger.info("=" * 60)
        logger.info("🚀 SINCRONIZAÇÃO INICIAL PÓS-DEPLOY")
        logger.info(f"📊 Buscando alterações dos últimos {janela_inicial} minutos")
        logger.info("=" * 60)

        app = create_app()
        with app.app_context():
            # 1️⃣ SINCRONIZAR FATURAMENTO INICIAL PRIMEIRO (ordem segura)
            logger.info("💰 Sincronização inicial do Faturamento...")
            faturamento_service = FaturamentoService()
            resultado_faturamento = faturamento_service.sincronizar_faturamento_incremental(
                minutos_janela=janela_inicial,
                primeira_execucao=True,
                minutos_status=STATUS_MINUTOS  # Usar o mesmo valor para status
            )

            if resultado_faturamento.get("sucesso"):
                logger.info("✅ Faturamento inicial sincronizado")
                logger.info(f"   - Novos: {resultado_faturamento.get('registros_novos', 0)}")
                logger.info(f"   - Atualizados: {resultado_faturamento.get('registros_atualizados', 0)}")

                # Mostrar estatísticas extras se disponíveis
                sincronizacoes = resultado_faturamento.get("sincronizacoes", {})
                if sincronizacoes:
                    logger.info(f"   - Relatórios: {sincronizacoes.get('relatorios_consolidados', 0)}")
                    logger.info(
                        f"   - Movimentações: {resultado_faturamento.get('movimentacoes_estoque', {}).get('movimentacoes_criadas', 0)}"
                    )
            else:
                logger.error(f"❌ Erro na sincronização inicial do Faturamento: {resultado_faturamento.get('erro')}")

            # 2️⃣ SINCRONIZAR CARTEIRA INICIAL DEPOIS (após faturamento protegido)
            logger.info("📦 Sincronização inicial da Carteira...")
            carteira_service = CarteiraService()
            resultado_carteira = carteira_service.sincronizar_incremental(
                minutos_janela=janela_inicial, primeira_execucao=True
            )

            if resultado_carteira.get("sucesso"):
                logger.info("✅ Carteira inicial sincronizada")
                logger.info(f"   - Pedidos: {resultado_carteira.get('pedidos_processados', 0)}")
                logger.info(f"   - Atualizados: {resultado_carteira.get('itens_atualizados', 0)}")
            else:
                logger.error(f"❌ Erro na sincronização inicial da Carteira: {resultado_carteira.get('erro')}")

    except Exception as e:
        logger.error(f"❌ Erro na sincronização inicial: {e}")


def main():
    """Função principal"""
    logger.info("=" * 60)
    logger.info("🎯 INICIANDO SCHEDULER DE SINCRONIZAÇÃO INCREMENTAL")
    logger.info("=" * 60)

    # PASSO 1: Executar sincronização inicial IMEDIATAMENTE
    logger.info("\n📌 Passo 1: Executando sincronização inicial (recuperação pós-deploy)...")
    executar_sincronizacao_inicial()

    # PASSO 2: Configurar scheduler para execuções periódicas
    logger.info("\n📌 Passo 2: Configurando execuções periódicas...")

    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")

    # Adicionar job periódico
    scheduler.add_job(
        func=executar_sincronizacao,
        trigger="interval",
        minutes=INTERVALO_MINUTOS,
        id="sincronizacao_incremental",
        name="Sincronização Incremental Carteira",
        next_run_time=datetime.now() + timedelta(minutes=INTERVALO_MINUTOS),
    )

    logger.info(f"✅ Scheduler configurado - próxima execução em {INTERVALO_MINUTOS} minutos")

    # Log importante sobre timezone
    import pytz

    tz_info = scheduler.timezone
    utc_now = datetime.now(pytz.UTC)
    local_now = utc_now.astimezone(tz_info)
    logger.info(f"⏰ Timezone configurado: {tz_info}")
    logger.info(f"   - UTC agora: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"   - Local agora: {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"   - Diferença UTC: {(local_now.hour - utc_now.hour) % 24} horas")

    # Handler para shutdown gracioso
    def shutdown_handler(signum, frame):
        logger.info("\n🛑 Encerrando scheduler...")
        scheduler.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # PASSO 3: Iniciar scheduler
    logger.info("\n📌 Passo 3: Iniciando scheduler...")
    logger.info("⏰ Aguardando próximas execuções...")
    logger.info("   Pressione Ctrl+C para parar\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Scheduler encerrado")


if __name__ == "__main__":
    main()
