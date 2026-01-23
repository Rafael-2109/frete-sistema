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
JANELA_REQUISICOES = int(os.environ.get('JANELA_REQUISICOES', 90))  # 90 minutos
JANELA_PEDIDOS = int(os.environ.get('JANELA_PEDIDOS', 90))  # 90 minutos (mesma janela)
JANELA_ALOCACOES = int(os.environ.get('JANELA_ALOCACOES', 90))  # 90 minutos (mesma janela)
JANELA_CTES = int(os.environ.get('JANELA_CTES', 90))  # ✅ 90 minutos para CTes
DIAS_ENTRADAS = int(os.environ.get('DIAS_ENTRADAS', 7))  # 7 dias para entradas de materiais
JANELA_CONTAS_RECEBER = int(os.environ.get('JANELA_CONTAS_RECEBER', 120))  # ✅ 120 minutos para Contas a Receber
JANELA_BAIXAS = int(os.environ.get('JANELA_BAIXAS', 120))  # ✅ 120 minutos para Baixas/Reconciliações
JANELA_CONTAS_PAGAR = int(os.environ.get('JANELA_CONTAS_PAGAR', 120))  # ✅ 120 minutos para Contas a Pagar
JANELA_NFDS = int(os.environ.get('JANELA_NFDS', 120))  # ✅ 120 minutos para NFDs de Devolução
JANELA_PALLET = int(os.environ.get('JANELA_PALLET', 5760))  # ✅ 5760 minutos (96h) para Pallets - mesmo que faturamento
DIAS_REVERSOES = int(os.environ.get('DIAS_REVERSOES', 30))  # ✅ 30 dias para Reversões de NF
JANELA_VALIDACAO_FISCAL = int(os.environ.get('JANELA_VALIDACAO_FISCAL', 120))  # ✅ 120 minutos para Validação Fiscal
JANELA_EXTRATOS = int(os.environ.get('JANELA_EXTRATOS', 120))  # ✅ 120 minutos para Sincronização de Extratos via Odoo
JANELA_PICKINGS = int(os.environ.get('JANELA_PICKINGS', 90))  # ✅ 90 minutos para Pickings de Recebimento (Fase 4)
MAX_RETRIES = 3
RETRY_DELAY = 5

# 🔴 IMPORTANTE: Services como variáveis globais (instanciados FORA do contexto)
faturamento_service = None
carteira_service = None
requisicao_service = None
pedido_service = None
alocacao_service = None
entrada_material_service = None
cte_service = None  # ✅ Service de CTes
contas_receber_service = None  # ✅ Service de Contas a Receber
baixas_service = None  # ✅ Service de Baixas/Reconciliações
contas_pagar_service = None  # ✅ Service de Contas a Pagar
nfd_service = None  # ✅ Service de NFDs de Devolução
pallet_service = None  # ✅ Service de Pallets
reversao_service = None  # ✅ Service de Reversões de NF
monitoramento_sync_service = None  # ✅ Service de Sincronização com Monitoramento
validacao_recebimento_job = None  # ✅ Job de Validação de Recebimento (Fase 1 + Fase 2)
validacao_ibscbs_job = None  # ✅ Job de Validação IBS/CBS (CTes + NF-es)
extratos_service = None  # ✅ Service de Sincronização de Extratos via Odoo
picking_recebimento_sync_service = None  # ✅ Service de Pickings de Recebimento (Fase 4)


def inicializar_services():
    """
    Inicializa os services FORA do contexto da aplicação.
    Isso evita problemas de SSL e contexto que ocorrem quando
    instanciados dentro do app.app_context()
    """
    global faturamento_service, carteira_service, requisicao_service, pedido_service, alocacao_service, entrada_material_service, cte_service, contas_receber_service, baixas_service, contas_pagar_service, nfd_service, pallet_service, reversao_service, monitoramento_sync_service, validacao_recebimento_job, validacao_ibscbs_job, extratos_service, picking_recebimento_sync_service

    try:
        # IMPORTANTE: Importar e instanciar FORA do contexto
        from app.odoo.services.faturamento_service import FaturamentoService
        from app.odoo.services.carteira_service import CarteiraService
        from app.odoo.services.requisicao_compras_service import RequisicaoComprasService
        from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado
        from app.odoo.services.alocacao_compras_service import AlocacaoComprasServiceOtimizado
        from app.odoo.services.entrada_material_service import EntradaMaterialService
        from app.odoo.services.cte_service import CteService  # ✅ Service de CTes
        from app.financeiro.services.sincronizacao_contas_receber_service import SincronizacaoContasReceberService  # ✅ Service de Contas a Receber
        from app.financeiro.services.sincronizacao_baixas_service import SincronizacaoBaixasService  # ✅ Service de Baixas
        from app.financeiro.services.sincronizacao_contas_pagar_service import SincronizacaoContasAPagarService  # ✅ Service de Contas a Pagar
        from app.devolucao.services.nfd_service import NFDService  # ✅ Service de NFDs de Devolução
        from app.pallet.services.sync_odoo_service import PalletSyncService  # ✅ Service de Pallets
        from app.devolucao.services.reversao_service import ReversaoService  # ✅ Service de Reversões de NF
        from app.devolucao.services.monitoramento_sync_service import MonitoramentoSyncService  # ✅ Service de Sync Monitoramento
        from app.recebimento.jobs.validacao_recebimento_job import ValidacaoRecebimentoJob  # ✅ Job de Validação de Recebimento (Fase 1 + Fase 2)
        from app.recebimento.jobs.validacao_ibscbs_job import ValidacaoIbsCbsJob  # ✅ Job de Validação IBS/CBS (CTes + NF-es)
        from app.financeiro.services.sincronizacao_extratos_service import SincronizacaoExtratosService  # ✅ Service de Extratos via Odoo
        from app.recebimento.services.picking_recebimento_sync_service import PickingRecebimentoSyncService  # ✅ Service de Pickings Recebimento (Fase 4)

        logger.info("🔧 Inicializando services FORA do contexto...")
        faturamento_service = FaturamentoService()
        carteira_service = CarteiraService()
        requisicao_service = RequisicaoComprasService()
        pedido_service = PedidoComprasServiceOtimizado()
        alocacao_service = AlocacaoComprasServiceOtimizado()
        entrada_material_service = EntradaMaterialService()
        cte_service = CteService()  # ✅ Instanciar service de CTes
        contas_receber_service = SincronizacaoContasReceberService()  # ✅ Instanciar service de Contas a Receber
        baixas_service = SincronizacaoBaixasService()  # ✅ Instanciar service de Baixas
        contas_pagar_service = SincronizacaoContasAPagarService()  # ✅ Instanciar service de Contas a Pagar
        nfd_service = NFDService()  # ✅ Instanciar service de NFDs de Devolução
        pallet_service = PalletSyncService()  # ✅ Instanciar service de Pallets
        reversao_service = ReversaoService()  # ✅ Instanciar service de Reversões de NF
        monitoramento_sync_service = MonitoramentoSyncService()  # ✅ Instanciar service de Sync Monitoramento
        validacao_recebimento_job = ValidacaoRecebimentoJob()  # ✅ Instanciar job de Validação de Recebimento (Fase 1 + Fase 2)
        validacao_ibscbs_job = ValidacaoIbsCbsJob()  # ✅ Instanciar job de Validação IBS/CBS (CTes + NF-es)
        extratos_service = SincronizacaoExtratosService()  # ✅ Instanciar service de Extratos via Odoo
        picking_recebimento_sync_service = PickingRecebimentoSyncService()  # ✅ Instanciar service de Pickings Recebimento (Fase 4)
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
    global faturamento_service, carteira_service, requisicao_service, pedido_service, alocacao_service, entrada_material_service, cte_service, contas_receber_service, baixas_service, contas_pagar_service, nfd_service, pallet_service, reversao_service, monitoramento_sync_service, validacao_recebimento_job, validacao_ibscbs_job, extratos_service, picking_recebimento_sync_service

    logger.info("=" * 60)
    logger.info(f"🔄 SINCRONIZAÇÃO DEFINITIVA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info(f"⚙️ Configurações:")
    logger.info(f"   - Intervalo: {INTERVALO_MINUTOS} minutos")
    logger.info(f"   - Faturamento: status={STATUS_FATURAMENTO}min (96h)")
    logger.info(f"   - Carteira: janela={JANELA_CARTEIRA}min")
    logger.info(f"   - Requisições: janela={JANELA_REQUISICOES}min")
    logger.info(f"   - Pedidos: janela={JANELA_PEDIDOS}min")
    logger.info(f"   - Alocações: janela={JANELA_ALOCACOES}min")
    logger.info(f"   - CTes: janela={JANELA_CTES}min")  # ✅ Adicionar CTes ao log
    logger.info(f"   - Entradas: dias={DIAS_ENTRADAS}")
    logger.info(f"   - Contas a Receber: janela={JANELA_CONTAS_RECEBER}min")  # ✅ Adicionar Contas a Receber ao log
    logger.info(f"   - Baixas: janela={JANELA_BAIXAS}min")  # ✅ Adicionar Baixas ao log
    logger.info(f"   - Contas a Pagar: janela={JANELA_CONTAS_PAGAR}min")  # ✅ Adicionar Contas a Pagar ao log
    logger.info(f"   - NFDs Devolução: janela={JANELA_NFDS}min")  # ✅ Adicionar NFDs ao log
    logger.info(f"   - Pallets: janela={JANELA_PALLET}min (96h)")  # ✅ Adicionar Pallets ao log
    logger.info(f"   - Reversões NF: dias={DIAS_REVERSOES}")  # ✅ Adicionar Reversões ao log
    logger.info(f"   - Monitoramento Sync: automático")  # ✅ Adicionar Monitoramento ao log
    logger.info(f"   - Validação Recebimento (Fase 1+2): janela={JANELA_VALIDACAO_FISCAL}min")  # ✅ Validação de Recebimento (Fase 1 Fiscal + Fase 2 NF×PO)
    logger.info(f"   - Validação IBS/CBS (CTe+NF-e): janela={JANELA_VALIDACAO_FISCAL}min")  # ✅ Validação IBS/CBS
    logger.info(f"   - Extratos via Odoo: janela={JANELA_EXTRATOS}min")  # ✅ Sincronização de Extratos via Odoo
    logger.info(f"   - Pickings Recebimento: janela={JANELA_PICKINGS}min")  # ✅ Pickings Recebimento (Fase 4)
    logger.info("=" * 60)

    # Verificar se services estão inicializados
    if not all([faturamento_service, carteira_service, requisicao_service, pedido_service, alocacao_service, entrada_material_service, cte_service, contas_receber_service, baixas_service, contas_pagar_service, nfd_service, pallet_service, reversao_service, monitoramento_sync_service, validacao_recebimento_job, validacao_ibscbs_job, extratos_service, picking_recebimento_sync_service]):
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

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Verificação de Exclusões")
        except Exception as e:
            pass

        # 2.5️⃣ VERIFICAÇÃO DE PEDIDOS EXCLUÍDOS DO ODOO - com retry
        sucesso_verificacao = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"🔍 Verificando pedidos excluídos do Odoo (tentativa {tentativa}/{MAX_RETRIES})...")

                # Usar service já instanciado
                resultado_verificacao = carteira_service.verificar_pedidos_excluidos_odoo()

                if resultado_verificacao.get("sucesso"):
                    sucesso_verificacao = True
                    logger.info("✅ Verificação de exclusões concluída!")
                    logger.info(f"   - Pedidos verificados: {resultado_verificacao.get('pedidos_verificados', 0)}")
                    logger.info(f"   - Pedidos excluídos: {resultado_verificacao.get('pedidos_excluidos', 0)}")
                    logger.info(f"   - Tempo: {resultado_verificacao.get('tempo_execucao', 0):.2f}s")

                    db.session.commit()
                    break
                else:
                    erro = resultado_verificacao.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Verificação: {erro}")

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
                logger.error(f"❌ Erro ao verificar pedidos excluídos: {e}")
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

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Requisições")
        except Exception as e:
            pass

        # 3️⃣ REQUISIÇÕES DE COMPRAS - com retry
        sucesso_requisicoes = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📋 Sincronizando Requisições (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_REQUISICOES} minutos")

                # Usar service já instanciado
                resultado_requisicoes = requisicao_service.sincronizar_requisicoes_incremental(
                    minutos_janela=JANELA_REQUISICOES,
                    primeira_execucao=False
                )

                if resultado_requisicoes.get("sucesso"):
                    sucesso_requisicoes = True
                    logger.info("✅ Requisições sincronizadas com sucesso!")
                    logger.info(f"   - Novas: {resultado_requisicoes.get('requisicoes_novas', 0)}")
                    logger.info(f"   - Atualizadas: {resultado_requisicoes.get('requisicoes_atualizadas', 0)}")
                    logger.info(f"   - Linhas processadas: {resultado_requisicoes.get('linhas_processadas', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_requisicoes.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Requisições: {erro}")

                    if "SSL" in str(erro) or "connection" in str(erro).lower():
                        if tentativa < MAX_RETRIES:
                            logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                            sleep(RETRY_DELAY)
                            # Reinicializar service
                            from app.odoo.services.requisicao_compras_service import RequisicaoComprasService
                            requisicao_service = RequisicaoComprasService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar requisições: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        # Reinicializar service
                        from app.odoo.services.requisicao_compras_service import RequisicaoComprasService
                        requisicao_service = RequisicaoComprasService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes dos Pedidos")
        except Exception as e:
            pass

        # 4️⃣ PEDIDOS DE COMPRAS - com retry
        sucesso_pedidos = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"🛒 Sincronizando Pedidos de Compra (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_PEDIDOS} minutos")

                # Usar service já instanciado
                resultado_pedidos = pedido_service.sincronizar_pedidos_incremental(
                    minutos_janela=JANELA_PEDIDOS,
                    primeira_execucao=False
                )

                if resultado_pedidos.get("sucesso"):
                    sucesso_pedidos = True
                    logger.info("✅ Pedidos sincronizados com sucesso!")
                    logger.info(f"   - Novos: {resultado_pedidos.get('pedidos_novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_pedidos.get('pedidos_atualizados', 0)}")
                    logger.info(f"   - Linhas processadas: {resultado_pedidos.get('linhas_processadas', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_pedidos.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Pedidos: {erro}")

                    if "SSL" in str(erro) or "connection" in str(erro).lower():
                        if tentativa < MAX_RETRIES:
                            logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                            sleep(RETRY_DELAY)
                            from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado
                            pedido_service = PedidoComprasServiceOtimizado()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar pedidos: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado
                        pedido_service = PedidoComprasServiceOtimizado()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Alocações")
        except Exception as e:
            pass

        # 5️⃣ ALOCAÇÕES DE COMPRAS - com retry
        sucesso_alocacoes = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"🔗 Sincronizando Alocações (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_ALOCACOES} minutos")

                # Usar service já instanciado
                resultado_alocacoes = alocacao_service.sincronizar_alocacoes_incremental(
                    minutos_janela=JANELA_ALOCACOES,
                    primeira_execucao=False
                )

                if resultado_alocacoes.get("sucesso"):
                    sucesso_alocacoes = True
                    logger.info("✅ Alocações sincronizadas com sucesso!")
                    logger.info(f"   - Novas: {resultado_alocacoes.get('alocacoes_novas', 0)}")
                    logger.info(f"   - Atualizadas: {resultado_alocacoes.get('alocacoes_atualizadas', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_alocacoes.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Alocações: {erro}")

                    if "SSL" in str(erro) or "connection" in str(erro).lower():
                        if tentativa < MAX_RETRIES:
                            logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                            sleep(RETRY_DELAY)
                            from app.odoo.services.alocacao_compras_service import AlocacaoComprasServiceOtimizado
                            alocacao_service = AlocacaoComprasServiceOtimizado()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar alocações: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.odoo.services.alocacao_compras_service import AlocacaoComprasServiceOtimizado
                        alocacao_service = AlocacaoComprasServiceOtimizado()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar conexões antes de Entradas
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Entradas")
        except Exception as e:
            pass

        # 7️⃣ ENTRADAS DE MATERIAIS - com retry
        sucesso_entradas = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📥 Sincronizando Entradas de Materiais (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Dias retroativos: {DIAS_ENTRADAS}")

                # Usar service já instanciado
                resultado_entradas = entrada_material_service.importar_entradas(
                    dias_retroativos=DIAS_ENTRADAS,
                    limite=None
                )

                if resultado_entradas.get("sucesso"):
                    sucesso_entradas = True
                    logger.info("✅ Entradas de materiais sincronizadas com sucesso!")
                    logger.info(f"   - Recebimentos processados: {resultado_entradas.get('recebimentos_processados', 0)}")
                    logger.info(f"   - Movimentações criadas: {resultado_entradas.get('movimentacoes_criadas', 0)}")
                    logger.info(f"   - Movimentações atualizadas: {resultado_entradas.get('movimentacoes_atualizadas', 0)}")
                    logger.info(f"   - Fornecedores grupo ignorados: {resultado_entradas.get('fornecedores_grupo_ignorados', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_entradas.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Entradas: {erro}")

                    if "SSL" in str(erro) or "connection" in str(erro).lower():
                        if tentativa < MAX_RETRIES:
                            logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                            sleep(RETRY_DELAY)
                            from app.odoo.services.entrada_material_service import EntradaMaterialService
                            entrada_material_service = EntradaMaterialService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar entradas: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.odoo.services.entrada_material_service import EntradaMaterialService
                        entrada_material_service = EntradaMaterialService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes dos CTes")
        except Exception as e:
            pass

        # 7️⃣ CTes - com retry
        sucesso_ctes = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📄 Sincronizando CTes (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_CTES} minutos")

                # Usar service já instanciado
                resultado_ctes = cte_service.importar_ctes(
                    minutos_janela=JANELA_CTES
                )

                if resultado_ctes.get("sucesso"):
                    sucesso_ctes = True
                    logger.info("✅ CTes sincronizados com sucesso!")
                    logger.info(f"   - Novos: {resultado_ctes.get('ctes_novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_ctes.get('ctes_atualizados', 0)}")
                    logger.info(f"   - Ignorados: {resultado_ctes.get('ctes_ignorados', 0)}")
                    logger.info(f"   - Processados: {resultado_ctes.get('ctes_processados', 0)}")

                    db.session.commit()
                    break
                else:
                    erros = resultado_ctes.get('erros', [])
                    logger.error(f"❌ Erro CTes: {erros[0] if erros else 'Erro desconhecido'}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.odoo.services.cte_service import CteService
                        cte_service = CteService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar CTes: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.odoo.services.cte_service import CteService
                        cte_service = CteService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Contas a Receber")
        except Exception as e:
            pass

        # 8️⃣ CONTAS A RECEBER - com retry
        sucesso_contas_receber = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"💰 Sincronizando Contas a Receber (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_CONTAS_RECEBER} minutos")

                # Usar service já instanciado
                resultado_contas_receber = contas_receber_service.sincronizar_incremental(
                    minutos_janela=JANELA_CONTAS_RECEBER
                )

                if resultado_contas_receber.get("sucesso"):
                    sucesso_contas_receber = True
                    logger.info("✅ Contas a Receber sincronizadas com sucesso!")
                    logger.info(f"   - Novos: {resultado_contas_receber.get('novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_contas_receber.get('atualizados', 0)}")
                    logger.info(f"   - Enriquecidos: {resultado_contas_receber.get('enriquecidos', 0)}")
                    logger.info(f"   - Snapshots: {resultado_contas_receber.get('snapshots_criados', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_contas_receber.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Contas a Receber: {erro}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.financeiro.services.sincronizacao_contas_receber_service import SincronizacaoContasReceberService
                        contas_receber_service = SincronizacaoContasReceberService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Contas a Receber: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.financeiro.services.sincronizacao_contas_receber_service import SincronizacaoContasReceberService
                        contas_receber_service = SincronizacaoContasReceberService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Baixas")
        except Exception as e:
            pass

        # 9️⃣ BAIXAS/RECONCILIAÇÕES - com retry
        sucesso_baixas = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"💵 Sincronizando Baixas/Reconciliações (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_BAIXAS} minutos")

                # Usar service já instanciado
                resultado_baixas = baixas_service.sincronizar_baixas(
                    janela_minutos=JANELA_BAIXAS
                )

                if resultado_baixas.get("titulos_processados", 0) >= 0:
                    sucesso_baixas = True
                    logger.info("✅ Baixas sincronizadas com sucesso!")
                    logger.info(f"   - Títulos processados: {resultado_baixas.get('titulos_processados', 0)}")
                    logger.info(f"   - Títulos com baixas: {resultado_baixas.get('titulos_com_baixas', 0)}")
                    logger.info(f"   - Reconciliações criadas: {resultado_baixas.get('reconciliacoes_criadas', 0)}")
                    logger.info(f"   - Vinculações automáticas: {resultado_baixas.get('vinculacoes_automaticas', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_baixas.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Baixas: {erro}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.financeiro.services.sincronizacao_baixas_service import SincronizacaoBaixasService
                        baixas_service = SincronizacaoBaixasService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Baixas: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.financeiro.services.sincronizacao_baixas_service import SincronizacaoBaixasService
                        baixas_service = SincronizacaoBaixasService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Extratos via Odoo")
        except Exception as e:
            pass

        # 9️⃣.5️⃣ SINCRONIZAÇÃO COMPLETA DE EXTRATOS - IMPORTAÇÃO + SYNC + VINCULAÇÃO CNAB
        sucesso_extratos = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📊 Sincronização Completa de Extratos (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_EXTRATOS} minutos")

                # =====================================================
                # PASSO 1: IMPORTAR NOVOS EXTRATOS DO ODOO
                # =====================================================
                logger.info("   [1/3] Importando novos extratos do Odoo...")
                resultado_importacao = extratos_service.importar_extratos_automatico(
                    dias_retroativos=7  # Últimos 7 dias
                )
                if resultado_importacao.get("success"):
                    stats_imp = resultado_importacao.get('stats', {})
                    logger.info(f"   ✅ Importados: {stats_imp.get('total_importados', 0)} novos extratos")
                else:
                    logger.warning(f"   ⚠️ Erro na importação: {resultado_importacao.get('error', 'Desconhecido')}")

                # =====================================================
                # PASSO 2: SINCRONIZAR STATUS VIA ODOO (write_date)
                # =====================================================
                logger.info("   [2/3] Sincronizando status via Odoo...")
                resultado_extratos = extratos_service.sincronizar_via_odoo(
                    janela_minutos=JANELA_EXTRATOS
                )

                if resultado_extratos.get("success"):
                    stats_ext = resultado_extratos.get('stats', {})
                    logger.info(f"   ✅ Status sync: {stats_ext.get('extratos_atualizados', 0)} atualizados")

                # =====================================================
                # PASSO 3: VINCULAR CNABs PENDENTES COM EXTRATOS
                # =====================================================
                logger.info("   [3/3] Vinculando CNABs a extratos...")
                resultado_vinc = extratos_service.vincular_cnab_extratos_pendentes()
                if resultado_vinc.get("success"):
                    stats_vinc = resultado_vinc.get('stats', {})
                    logger.info(
                        f"   ✅ Vinculação: {stats_vinc.get('matches_encontrados', 0)} matches, "
                        f"{stats_vinc.get('extratos_atualizados', 0)} extratos atualizados, "
                        f"{stats_vinc.get('odoo_reconciliados', 0)} reconciliados no Odoo"
                    )
                else:
                    logger.warning(f"   ⚠️ Erro na vinculação: {resultado_vinc.get('error', 'Desconhecido')}")

                # Resumo final
                sucesso_extratos = True
                logger.info("✅ Sincronização completa de extratos concluída!")
                logger.info(f"   - Importados: {resultado_importacao.get('stats', {}).get('total_importados', 0)}")
                logger.info(f"   - Status atualizados: {resultado_extratos.get('stats', {}).get('extratos_atualizados', 0)}")
                logger.info(f"   - CNABs vinculados: {resultado_vinc.get('stats', {}).get('matches_encontrados', 0)}")

                db.session.commit()
                break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Extratos: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.financeiro.services.sincronizacao_extratos_service import SincronizacaoExtratosService
                        extratos_service = SincronizacaoExtratosService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Contas a Pagar")
        except Exception as e:
            pass

        # 🔟 CONTAS A PAGAR - com retry
        sucesso_contas_pagar = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"💸 Sincronizando Contas a Pagar (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_CONTAS_PAGAR} minutos")

                # Usar service já instanciado
                resultado_contas_pagar = contas_pagar_service.sincronizar_incremental(
                    minutos_janela=JANELA_CONTAS_PAGAR
                )

                if resultado_contas_pagar.get("sucesso"):
                    sucesso_contas_pagar = True
                    logger.info("✅ Contas a Pagar sincronizadas com sucesso!")
                    logger.info(f"   - Novos: {resultado_contas_pagar.get('novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_contas_pagar.get('atualizados', 0)}")
                    logger.info(f"   - Erros: {resultado_contas_pagar.get('erros', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_contas_pagar.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Contas a Pagar: {erro}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.financeiro.services.sincronizacao_contas_pagar_service import SincronizacaoContasAPagarService
                        contas_pagar_service = SincronizacaoContasAPagarService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Contas a Pagar: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.financeiro.services.sincronizacao_contas_pagar_service import SincronizacaoContasAPagarService
                        contas_pagar_service = SincronizacaoContasAPagarService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das NFDs de Devolução")
        except Exception as e:
            pass

        # 1️⃣1️⃣ NFDs DE DEVOLUÇÃO - com retry
        sucesso_nfds = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📦 Sincronizando NFDs de Devolução (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_NFDS} minutos")

                # Usar service já instanciado
                resultado_nfds = nfd_service.importar_nfds(
                    minutos_janela=JANELA_NFDS
                )

                if resultado_nfds.get("sucesso"):
                    sucesso_nfds = True
                    logger.info("✅ NFDs de Devolução sincronizadas com sucesso!")
                    logger.info(f"   - Processadas: {resultado_nfds.get('nfds_processadas', 0)}")
                    logger.info(f"   - Novas: {resultado_nfds.get('nfds_novas', 0)}")
                    logger.info(f"   - Vinculadas: {resultado_nfds.get('nfds_vinculadas', 0)}")
                    logger.info(f"   - Órfãs: {resultado_nfds.get('nfds_orfas', 0)}")
                    logger.info(f"   - Ocorrências criadas: {resultado_nfds.get('ocorrencias_criadas', 0)}")
                    logger.info(f"   - Linhas criadas: {resultado_nfds.get('linhas_criadas', 0)}")

                    db.session.commit()
                    break
                else:
                    erros = resultado_nfds.get('erros', [])
                    logger.error(f"❌ Erro NFDs: {erros[0] if erros else 'Erro desconhecido'}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.devolucao.services.nfd_service import NFDService
                        nfd_service = NFDService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar NFDs de Devolução: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.devolucao.services.nfd_service import NFDService
                        nfd_service = NFDService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes dos Pallets")
        except Exception as e:
            pass

        # 1️⃣2️⃣ PALLETS - com retry
        sucesso_pallets = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📦 Sincronizando Pallets (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_PALLET} minutos (96h)")

                # Converter minutos em dias para o service
                dias_retroativos = JANELA_PALLET // 1440  # 1440 minutos = 1 dia
                if dias_retroativos < 1:
                    dias_retroativos = 1

                # Usar service já instanciado
                resultado_pallets = pallet_service.sincronizar_tudo(dias_retroativos=dias_retroativos)

                if resultado_pallets.get("total_novos", 0) >= 0:
                    sucesso_pallets = True
                    logger.info("✅ Pallets sincronizados com sucesso!")
                    logger.info(f"   - Remessas novas: {resultado_pallets.get('remessas', {}).get('novos', 0)}")
                    logger.info(f"   - Vendas novas: {resultado_pallets.get('vendas', {}).get('novos', 0)}")
                    logger.info(f"   - Devoluções novas: {resultado_pallets.get('devolucoes', {}).get('novos', 0)}")
                    logger.info(f"   - Recusas novas: {resultado_pallets.get('recusas', {}).get('novos', 0)}")
                    logger.info(f"   - Total novos: {resultado_pallets.get('total_novos', 0)}")
                    logger.info(f"   - Total baixas: {resultado_pallets.get('total_baixas', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_pallets.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Pallets: {erro}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.pallet.services.sync_odoo_service import PalletSyncService
                        pallet_service = PalletSyncService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Pallets: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.pallet.services.sync_odoo_service import PalletSyncService
                        pallet_service = PalletSyncService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Reversões de NF")
        except Exception as e:
            pass

        # 1️⃣3️⃣ REVERSÕES DE NF - com retry
        sucesso_reversoes = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"🔄 Sincronizando Reversões de NF (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Dias retroativos: {DIAS_REVERSOES}")

                # Usar service já instanciado
                resultado_reversoes = reversao_service.importar_reversoes(
                    dias=DIAS_REVERSOES
                )

                if resultado_reversoes.get("sucesso"):
                    sucesso_reversoes = True
                    logger.info("✅ Reversões sincronizadas com sucesso!")
                    logger.info(f"   - Processadas: {resultado_reversoes.get('reversoes_processadas', 0)}")
                    logger.info(f"   - NFDs criadas: {resultado_reversoes.get('nfds_criadas', 0)}")
                    logger.info(f"   - Vinculadas monitoramento: {resultado_reversoes.get('vinculadas_monitoramento', 0)}")
                    logger.info(f"   - Ocorrências criadas: {resultado_reversoes.get('ocorrencias_criadas', 0)}")

                    db.session.commit()
                    break
                else:
                    erros = resultado_reversoes.get('erros', [])
                    logger.error(f"❌ Erro Reversões: {erros[0] if erros else 'Erro desconhecido'}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.devolucao.services.reversao_service import ReversaoService
                        reversao_service = ReversaoService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Reversões: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.devolucao.services.reversao_service import ReversaoService
                        reversao_service = ReversaoService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes do Sync Monitoramento")
        except Exception as e:
            pass

        # 1️⃣4️⃣ SYNC MONITORAMENTO - com retry
        sucesso_monitoramento = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📊 Sincronizando com Monitoramento (tentativa {tentativa}/{MAX_RETRIES})...")

                # Usar service já instanciado
                resultado_monitoramento = monitoramento_sync_service.sincronizar_monitoramento()

                if resultado_monitoramento.get("sucesso"):
                    sucesso_monitoramento = True
                    logger.info("✅ Monitoramento sincronizado com sucesso!")
                    logger.info(f"   - Entregas processadas: {resultado_monitoramento.get('entregas_processadas', 0)}")
                    logger.info(f"   - NFDs criadas: {resultado_monitoramento.get('nfds_criadas', 0)}")
                    logger.info(f"   - Ocorrências criadas: {resultado_monitoramento.get('ocorrencias_criadas', 0)}")

                    db.session.commit()
                    break
                else:
                    erros = resultado_monitoramento.get('erros', [])
                    logger.error(f"❌ Erro Monitoramento: {erros[0] if erros else 'Erro desconhecido'}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar service
                        from app.devolucao.services.monitoramento_sync_service import MonitoramentoSyncService
                        monitoramento_sync_service = MonitoramentoSyncService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Monitoramento: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.devolucao.services.monitoramento_sync_service import MonitoramentoSyncService
                        monitoramento_sync_service = MonitoramentoSyncService()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Validação Fiscal")
        except Exception as e:
            pass

        # 1️⃣5️⃣ VALIDAÇÃO DE RECEBIMENTO (FASE 1 + FASE 2) - com retry
        sucesso_validacao_recebimento = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"🔍 Validando Recebimento - Fase 1 (Fiscal) + Fase 2 (NF×PO) (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_VALIDACAO_FISCAL} minutos")

                # Usar job já instanciado (executa AMBAS as fases + sync De-Para)
                resultado_validacao = validacao_recebimento_job.executar(
                    minutos_janela=JANELA_VALIDACAO_FISCAL
                )

                if resultado_validacao.get("sucesso"):
                    sucesso_validacao_recebimento = True
                    logger.info("✅ Validação de Recebimento concluída!")

                    # Sync De-Para
                    sync_depara = resultado_validacao.get('sync_depara', {})
                    logger.info(f"   - De-Para importados: {sync_depara.get('importados', 0)}, atualizados: {sync_depara.get('atualizados', 0)}")

                    # Fase 1 - Fiscal
                    fase1 = resultado_validacao.get('fase1_fiscal', {})
                    logger.info(f"   - [Fase 1] Validados: {fase1.get('dfes_validados', 0)}, Aprovados: {fase1.get('dfes_aprovados', 0)}, Bloqueados: {fase1.get('dfes_bloqueados', 0)}, 1ª Compra: {fase1.get('dfes_primeira_compra', 0)}")

                    # Fase 2 - NF×PO
                    fase2 = resultado_validacao.get('fase2_nf_po', {})
                    logger.info(f"   - [Fase 2] Validados: {fase2.get('dfes_validados', 0)}, Aprovados: {fase2.get('dfes_aprovados', 0)}, Bloqueados: {fase2.get('dfes_bloqueados', 0)}")

                    logger.info(f"   - DFEs processados: {resultado_validacao.get('dfes_processados', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_validacao.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Validação Recebimento: {erro}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar job
                        from app.recebimento.jobs.validacao_recebimento_job import ValidacaoRecebimentoJob
                        validacao_recebimento_job = ValidacaoRecebimentoJob()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao validar recebimento: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.recebimento.jobs.validacao_recebimento_job import ValidacaoRecebimentoJob
                        validacao_recebimento_job = ValidacaoRecebimentoJob()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre jobs
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Validação IBS/CBS")
        except Exception as e:
            pass

        # 1️⃣6️⃣ VALIDAÇÃO IBS/CBS (CTes + NF-es) - com retry
        sucesso_validacao_ibscbs = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📋 Validando IBS/CBS - CTes + NF-es (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_VALIDACAO_FISCAL} minutos")

                # Usar job já instanciado
                resultado_ibscbs = validacao_ibscbs_job.executar(
                    minutos_janela=JANELA_VALIDACAO_FISCAL
                )

                if resultado_ibscbs.get("sucesso"):
                    sucesso_validacao_ibscbs = True
                    logger.info("✅ Validação IBS/CBS concluída!")
                    logger.info(f"   - CTes processados: {resultado_ibscbs.get('ctes_processados', 0)}, pendências: {resultado_ibscbs.get('ctes_pendencias', 0)}")
                    logger.info(f"   - NF-es processadas: {resultado_ibscbs.get('nfes_processadas', 0)}, pendências: {resultado_ibscbs.get('nfes_pendencias', 0)}")
                    logger.info(f"   - Erros: {resultado_ibscbs.get('erros', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_ibscbs.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Validação IBS/CBS: {erro}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        # Reinicializar job
                        from app.recebimento.jobs.validacao_ibscbs_job import ValidacaoIbsCbsJob
                        validacao_ibscbs_job = ValidacaoIbsCbsJob()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao validar IBS/CBS: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.recebimento.jobs.validacao_ibscbs_job import ValidacaoIbsCbsJob
                        validacao_ibscbs_job = ValidacaoIbsCbsJob()
                    except Exception as e:
                        pass
                else:
                    break

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Pickings Recebimento")
        except Exception as e:
            pass

        # 1️⃣7️⃣ PICKINGS RECEBIMENTO (Fase 4) - com retry
        sucesso_pickings_recebimento = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📦 Sincronizando Pickings Recebimento (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_PICKINGS} minutos")

                resultado_pickings = picking_recebimento_sync_service.sincronizar_pickings_incremental(
                    minutos_janela=JANELA_PICKINGS,
                    primeira_execucao=False
                )

                if resultado_pickings.get("sucesso"):
                    sucesso_pickings_recebimento = True
                    logger.info("✅ Pickings Recebimento sincronizados!")
                    logger.info(f"   - Novos: {resultado_pickings.get('novos', 0)}")
                    logger.info(f"   - Atualizados: {resultado_pickings.get('atualizados', 0)}")

                    db.session.commit()
                    break
                else:
                    erro = resultado_pickings.get('erro', 'Erro desconhecido')
                    logger.error(f"❌ Erro Pickings Recebimento: {erro}")

                    if tentativa < MAX_RETRIES:
                        logger.info(f"🔄 Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                        sleep(RETRY_DELAY)
                        from app.recebimento.services.picking_recebimento_sync_service import PickingRecebimentoSyncService
                        picking_recebimento_sync_service = PickingRecebimentoSyncService()
                    else:
                        break

            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar Pickings Recebimento: {e}")
                if tentativa < MAX_RETRIES and ("SSL" in str(e) or "connection" in str(e).lower()):
                    logger.info(f"🔄 Tentando reconectar ({tentativa}/{MAX_RETRIES})...")
                    sleep(RETRY_DELAY)
                    try:
                        db.session.rollback()
                        db.session.remove()
                        from app.recebimento.services.picking_recebimento_sync_service import PickingRecebimentoSyncService
                        picking_recebimento_sync_service = PickingRecebimentoSyncService()
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
        total_sucesso = sum([sucesso_faturamento, sucesso_carteira, sucesso_verificacao, sucesso_requisicoes, sucesso_pedidos, sucesso_alocacoes, sucesso_entradas, sucesso_ctes, sucesso_contas_receber, sucesso_baixas, sucesso_extratos, sucesso_contas_pagar, sucesso_nfds, sucesso_pallets, sucesso_reversoes, sucesso_monitoramento, sucesso_validacao_recebimento, sucesso_validacao_ibscbs, sucesso_pickings_recebimento])

        if total_sucesso == 19:
            logger.info("✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO!")
        elif total_sucesso >= 17:
            logger.info(f"⚠️ Sincronização parcial - {total_sucesso}/19 módulos OK")
            if not sucesso_faturamento:
                logger.info("   ❌ Faturamento: FALHOU")
            if not sucesso_carteira:
                logger.info("   ❌ Carteira: FALHOU")
            if not sucesso_verificacao:
                logger.info("   ❌ Verificação Exclusões: FALHOU")
            if not sucesso_requisicoes:
                logger.info("   ❌ Requisições: FALHOU")
            if not sucesso_pedidos:
                logger.info("   ❌ Pedidos: FALHOU")
            if not sucesso_alocacoes:
                logger.info("   ❌ Alocações: FALHOU")
            if not sucesso_entradas:
                logger.info("   ❌ Entradas de Materiais: FALHOU")
            if not sucesso_ctes:
                logger.info("   ❌ CTes: FALHOU")
            if not sucesso_contas_receber:
                logger.info("   ❌ Contas a Receber: FALHOU")
            if not sucesso_baixas:
                logger.info("   ❌ Baixas/Reconciliações: FALHOU")
            if not sucesso_extratos:
                logger.info("   ❌ Extratos via Odoo: FALHOU")
            if not sucesso_contas_pagar:
                logger.info("   ❌ Contas a Pagar: FALHOU")
            if not sucesso_nfds:
                logger.info("   ❌ NFDs Devolução: FALHOU")
            if not sucesso_pallets:
                logger.info("   ❌ Pallets: FALHOU")
            if not sucesso_reversoes:
                logger.info("   ❌ Reversões NF: FALHOU")
            if not sucesso_monitoramento:
                logger.info("   ❌ Sync Monitoramento: FALHOU")
            if not sucesso_validacao_recebimento:
                logger.info("   ❌ Validação Recebimento (Fase 1+2): FALHOU")
            if not sucesso_validacao_ibscbs:
                logger.info("   ❌ Validação IBS/CBS (CTe+NF-e): FALHOU")
            if not sucesso_pickings_recebimento:
                logger.info("   ❌ Pickings Recebimento (Fase 4): FALHOU")
        else:
            logger.error(f"❌ Sincronização com falhas graves - apenas {total_sucesso}/19 módulos OK")
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