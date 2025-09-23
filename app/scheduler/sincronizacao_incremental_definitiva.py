#!/usr/bin/env python3
"""
Scheduler de Sincronização Incremental DEFINITIVO
==================================================

VERSÃO FINAL com TODAS as correções:
1. Valores de janela CORRETOS para cada serviço
2. Services instanciados FORA do contexto (como no que funciona)
3. Tratamento robusto de erros e reconexão

Valores CORRETOS:
- Execução: A cada 30 minutos
- Faturamento: minutos_status=5760 (96 horas) para verificar status
- Carteira: minutos_janela=40 (40 minutos)

Autor: Sistema de Fretes
Data: 2025-09-22
"""

import logging
import signal
import sys
import os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from time import sleep

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 🔧 CONFIGURAÇÕES DEFINITIVAS E CORRETAS
INTERVALO_MINUTOS = int(os.environ.get('SYNC_INTERVAL_MINUTES', 30))
JANELA_CARTEIRA = int(os.environ.get('JANELA_CARTEIRA', 40))
STATUS_FATURAMENTO = int(os.environ.get('STATUS_FATURAMENTO', 5760))
MAX_RETRIES = 3
RETRY_DELAY = 5

# 🔴 IMPORTANTE: Services como variáveis globais (instanciados FORA do contexto)
faturamento_service = None
carteira_service = None


def inicializar_services():
    """
    Inicializa os services FORA do contexto da aplicação.
    Isso evita problemas de SSL e contexto que ocorrem quando
    instanciados dentro do app.app_context()
    """
    global faturamento_service, carteira_service

    try:
        # IMPORTANTE: Importar e instanciar FORA do contexto
        from app.odoo.services.faturamento_service import FaturamentoService
        from app.odoo.services.carteira_service import CarteiraService

        logger.info("🔧 Inicializando services FORA do contexto...")
        faturamento_service = FaturamentoService()
        carteira_service = CarteiraService()
        logger.info("✅ Services inicializados com sucesso")

        return True

    except Exception as e:
        logger.error(f"❌ Erro ao inicializar services: {e}")
        return False


def executar_sincronizacao():
    """
    Executa sincronização usando services já instanciados
    Similar ao que funciona em SincronizacaoIntegradaService
    """
    global faturamento_service, carteira_service

    logger.info("=" * 60)
    logger.info(f"🔄 SINCRONIZAÇÃO DEFINITIVA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info(f"⚙️ Configurações:")
    logger.info(f"   - Intervalo: {INTERVALO_MINUTOS} minutos")
    logger.info(f"   - Faturamento: status={STATUS_FATURAMENTO}min (96h)")
    logger.info(f"   - Carteira: janela={JANELA_CARTEIRA}min")
    logger.info("=" * 60)

    # Verificar se services estão inicializados
    if not faturamento_service or not carteira_service:
        logger.warning("⚠️ Services não inicializados, tentando inicializar...")
        if not inicializar_services():
            logger.error("❌ Falha ao inicializar services")
            return

    from app import create_app, db
    app = create_app()

    with app.app_context():
        # Limpar conexões antigas
        try:
            db.session.close()
            db.engine.dispose()
            logger.info("♻️ Conexões de banco limpas")
        except Exception as e:
            pass

        sucesso_faturamento = False
        sucesso_carteira = False

        # 1️⃣ FATURAMENTO - com retry
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"💰 Sincronizando Faturamento (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Status: {STATUS_FATURAMENTO} minutos (26 horas)")

                # Usar service já instanciado (FORA do contexto)
                resultado_faturamento = faturamento_service.sincronizar_faturamento_incremental(
                    primeira_execucao=False,
                    minutos_status=STATUS_FATURAMENTO
                )

                if resultado_faturamento.get("sucesso"):
                    sucesso_faturamento = True
                    logger.info("✅ Faturamento sincronizado com sucesso!")
                    logger.info(f"   - Novos: {resultado_faturamento.get('registros_novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_faturamento.get('registros_atualizados', 0)}")

                    mov_estoque = resultado_faturamento.get('movimentacoes_estoque', {})
                    if mov_estoque.get('movimentacoes_criadas'):
                        logger.info(f"   - Movimentações de estoque: {mov_estoque['movimentacoes_criadas']}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_faturamento.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Faturamento: {erro}")

                    if "SSL" in str(erro) or "connection" in str(erro).lower():
                        if tentativa < MAX_RETRIES:
                            logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                            sleep(RETRY_DELAY)
                            # Reinicializar service
                            from app.odoo.services.faturamento_service import FaturamentoService
                            faturamento_service = FaturamentoService()
                    else:
                        break  # Erro não é de conexão, não adianta retry

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar faturamento: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        # Reinicializar service
                        from app.odoo.services.faturamento_service import FaturamentoService
                        faturamento_service = FaturamentoService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre os services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Carteira")
        except Exception as e:
            pass

        # 2️⃣ CARTEIRA - com retry
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📦 Sincronizando Carteira (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_CARTEIRA} minutos")

                # Usar service já instanciado (FORA do contexto)
                resultado_carteira = carteira_service.sincronizar_carteira_odoo_com_gestao_quantidades(
                    usar_filtro_pendente=False,
                    modo_incremental=True,
                    minutos_janela=JANELA_CARTEIRA,
                    primeira_execucao=False
                )

                if resultado_carteira.get("sucesso"):
                    sucesso_carteira = True
                    logger.info("✅ Carteira sincronizada com sucesso!")
                    logger.info(f"   - Pedidos: {resultado_carteira.get('pedidos_processados', 0)}")
                    logger.info(f"   - Atualizados: {resultado_carteira.get('itens_atualizados', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_carteira.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Carteira: {erro}")

                    # Verificar se é erro de campos obrigatórios
                    if "cod_uf" in str(erro).lower() or "nome_cidade" in str(erro).lower():
                        logger.warning("⚠️ Erro de campos obrigatórios detectado")
                        logger.info("   O tratamento de fallback deve estar funcionando no service")
                        # Continuar mesmo assim, pois o service tem tratamento

                    if "SSL" in str(erro) or "connection" in str(erro).lower():
                        if tentativa < MAX_RETRIES:
                            logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                            sleep(RETRY_DELAY)
                            # Reinicializar service
                            from app.odoo.services.carteira_service import CarteiraService
                            carteira_service = CarteiraService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar carteira: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        # Reinicializar service
                        from app.odoo.services.carteira_service import CarteiraService
                        carteira_service = CarteiraService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar conexões ao final
        try:
            db.session.remove()
            db.engine.dispose()
        except Exception as e:
            pass

        # Resumo final
        logger.info("=" * 60)
        if sucesso_faturamento and sucesso_carteira:
            logger.info("✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO!")
        elif sucesso_faturamento:
            logger.info("⚠️ Sincronização parcial - Apenas Faturamento OK")
        elif sucesso_carteira:
            logger.info("⚠️ Sincronização parcial - Apenas Carteira OK")
        else:
            logger.error("❌ Sincronização falhou completamente")
        logger.info("=" * 60)


def executar_inicial():
    """
    Execução inicial com janelas maiores para recuperação pós-deploy
    """
    global JANELA_CARTEIRA, JANELA_FATURAMENTO

    logger.info("🚀 SINCRONIZAÇÃO INICIAL (recuperação pós-deploy)")
    logger.info("   Usando janelas maiores para primeira execução...")

    # Backup dos valores originais
    janela_carteira_original = JANELA_CARTEIRA

    # Janelas maiores para primeira execução
    JANELA_CARTEIRA = 120          # 2 horas

    try:
        executar_sincronizacao()
    finally:
        # Restaurar valores originais
        JANELA_CARTEIRA = janela_carteira_original


def main():
    """
    Função principal - inicializa services FORA do contexto e configura scheduler
    """
    logger.info("=" * 60)
    logger.info("🎯 INICIANDO SCHEDULER DEFINITIVO")
    logger.info("=" * 60)
    logger.info("⚙️ CONFIGURAÇÕES FINAIS:")
    logger.info(f"   - Execução: a cada {INTERVALO_MINUTOS} minutos")
    logger.info(f"   - Faturamento: status de {STATUS_FATURAMENTO} minutos (96 horas)")
    logger.info(f"   - Carteira: janela de {JANELA_CARTEIRA} minutos")
    logger.info("=" * 60)

    # 🔴 CRÍTICO: Inicializar services ANTES de tudo (FORA do contexto)
    if not inicializar_services():
        logger.error("❌ Falha crítica ao inicializar services. Abortando.")
        sys.exit(1)

    # Executar sincronização inicial
    executar_inicial()

    # Configurar scheduler
    scheduler = BlockingScheduler(
        timezone="America/Sao_Paulo",
        job_defaults={
            'coalesce': True,
            'max_instances': 1
        }
    )

    scheduler.add_job(
        func=executar_sincronizacao,
        trigger="interval",
        minutes=INTERVALO_MINUTOS,
        id="sincronizacao_definitiva",
        name="Sincronização Definitiva (Services Fora do Contexto)",
        max_instances=1,
        misfire_grace_time=300,
        replace_existing=True
    )

    logger.info("=" * 60)
    logger.info("✅ Scheduler configurado com TODAS as correções:")
    logger.info("   1. Valores de janela corretos para cada serviço")
    logger.info("   2. Services instanciados FORA do contexto")
    logger.info("   3. Tratamento robusto de erros e reconexão")
    logger.info(f"   Próxima execução em {INTERVALO_MINUTOS} minutos...")
    logger.info("=" * 60)

    # Handlers de shutdown
    def shutdown(signum, frame):
        logger.info("🛑 Recebido sinal de shutdown, encerrando...")
        scheduler.shutdown(wait=False)
        logger.info("👋 Scheduler encerrado com sucesso")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Iniciar scheduler
    try:
        logger.info("▶️  Scheduler iniciado e aguardando...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Scheduler interrompido")
    except Exception as e:
        logger.error(f"❌ Erro fatal no scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()