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
- Carteira: minutos_janela=70 (70 minutos = 2×intervalo + 10min gordura)

Autor: Sistema de Fretes
Data: 2025-09-22
"""

import logging
import signal
import sys
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from time import sleep
from app.utils.timezone import agora_utc_naive


# Dual handler: arquivo (debug in-session) + stderr (capturado pelo Render)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

os.makedirs('logs', exist_ok=True)
_file_handler = logging.FileHandler('logs/sincronizacao_incremental.log')
_file_handler.setFormatter(_formatter)
logger.addHandler(_file_handler)

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(_formatter)
logger.addHandler(_stderr_handler)

# 🔧 CONFIGURAÇÕES DEFINITIVAS E CORRETAS
INTERVALO_MINUTOS = int(os.environ.get('SYNC_INTERVAL_MINUTES', 30))
JANELA_CARTEIRA = int(os.environ.get('JANELA_CARTEIRA', 70))  # 70min = 2×30min intervalo + 10min gordura
STATUS_FATURAMENTO = int(os.environ.get('STATUS_FATURAMENTO', 2880))  # 48h — reduzido de 96h (2026-04-14)
JANELA_REQUISICOES = int(os.environ.get('JANELA_REQUISICOES', 90))  # 90 minutos
JANELA_PEDIDOS = int(os.environ.get('JANELA_PEDIDOS', 90))  # 90 minutos (mesma janela)
JANELA_ALOCACOES = int(os.environ.get('JANELA_ALOCACOES', 90))  # 90 minutos (mesma janela)
JANELA_CTES = int(os.environ.get('JANELA_CTES', 90))  # ✅ 90 minutos para CTes
DIAS_ENTRADAS = int(os.environ.get('DIAS_ENTRADAS', 7))  # 7 dias para entradas de materiais
JANELA_CONTAS_RECEBER = int(os.environ.get('JANELA_CONTAS_RECEBER', 120))  # ✅ 120 minutos para Contas a Receber
JANELA_BAIXAS = int(os.environ.get('JANELA_BAIXAS', 120))  # ✅ 120 minutos para Baixas/Reconciliações
JANELA_CONTAS_PAGAR = int(os.environ.get('JANELA_CONTAS_PAGAR', 120))  # ✅ 120 minutos para Contas a Pagar
JANELA_NFDS = int(os.environ.get('JANELA_NFDS', 120))  # ✅ 120 minutos para NFDs de Devolução
JANELA_PALLET = int(os.environ.get('JANELA_PALLET', 2880))  # 48h — reduzido de 96h (2026-04-14 O3)
DIAS_REVERSOES = int(os.environ.get('DIAS_REVERSOES', 7))  # 7 dias — reduzido de 30 (2026-04-14 O3)
JANELA_VALIDACAO_FISCAL = int(os.environ.get('JANELA_VALIDACAO_FISCAL', 120))  # ✅ 120 minutos para Validação Fiscal
JANELA_EXTRATOS = int(os.environ.get('JANELA_EXTRATOS', 120))  # ✅ 120 minutos para Sincronização de Extratos via Odoo
JANELA_PICKINGS = int(os.environ.get('JANELA_PICKINGS', 90))  # ✅ 90 minutos para Pickings de Recebimento (Fase 4)
MAX_RETRIES = 3
RETRY_DELAY = 5

# Reindexação diária de embeddings (20º módulo)
EMBEDDINGS_REINDEX_ENABLED = os.environ.get("EMBEDDINGS_REINDEX_ENABLED", "true").lower() == "true"
EMBEDDINGS_REINDEX_HOUR = int(os.environ.get("EMBEDDINGS_REINDEX_HOUR", "3"))
_ultima_reindexacao_embeddings = None  # Timestamp da ultima reindexacao bem-sucedida

# Varredura diária de segurança (21º módulo)
SEGURANCA_SCAN_ENABLED = os.environ.get("SEGURANCA_SCAN_ENABLED", "true").lower() == "true"
SEGURANCA_SCAN_HOUR = int(os.environ.get("SEGURANCA_SCAN_HOUR", "4"))  # 4h da manhã (após embeddings às 3h)
_ultima_varredura_seguranca = None  # Timestamp da ultima varredura bem-sucedida

# Limpeza semanal de entidades órfãs do Knowledge Graph (22º módulo)
KG_CLEANUP_ENABLED = os.environ.get("KG_CLEANUP_ENABLED", "true").lower() == "true"
KG_CLEANUP_WEEKDAY = int(os.environ.get("KG_CLEANUP_WEEKDAY", "6"))  # 0=Mon, 6=Sun
KG_CLEANUP_HOUR = int(os.environ.get("KG_CLEANUP_HOUR", "5"))  # 5h (após segurança 4h)
_ultimo_kg_cleanup = None  # Timestamp do ultimo cleanup bem-sucedido

# Auditoria diária de inconsistências financeiras Local × Odoo (23º módulo)
AUDITORIA_FINANCEIRA_ENABLED = os.environ.get("AUDITORIA_FINANCEIRA_ENABLED", "true").lower() == "true"
AUDITORIA_FINANCEIRA_HOUR = int(os.environ.get("AUDITORIA_FINANCEIRA_HOUR", "6"))  # 6h (após KG cleanup 5h)
_ultima_auditoria_financeira = None  # Timestamp da ultima auditoria bem-sucedida

# Improvement Dialogue batch — sugestoes de melhoria Agent SDK -> Claude Code (25º módulo)
# Roda 2x/dia: 07:00 (catch-up noturno) e 10:00 (pronto antes do D8 cron as 11:00)
IMPROVEMENT_DIALOGUE_ENABLED = os.environ.get("AGENT_IMPROVEMENT_DIALOGUE", "false").lower() == "true"
IMPROVEMENT_DIALOGUE_HOURS = [7, 10]  # Horarios de execucao
_ultimo_improvement_dialogue = None  # Timestamp da ultima execucao bem-sucedida

# Fechamento mensal automatico de custeio (26º módulo) — Sprint 2 C10
# Roda mensalmente: dia 5 às 04:00. Idempotente (constraint UNIQUE em custo_mensal).
FECHAR_MES_CUSTEIO_ENABLED = os.environ.get("FECHAR_MES_CUSTEIO_ENABLED", "true").lower() == "true"
FECHAR_MES_CUSTEIO_DAY = int(os.environ.get("FECHAR_MES_CUSTEIO_DAY", "5"))
FECHAR_MES_CUSTEIO_HOUR = int(os.environ.get("FECHAR_MES_CUSTEIO_HOUR", "4"))
_ultimo_fechamento_mes_custeio = None  # Timestamp do ultimo fechamento bem-sucedido

# Health check diário de custeio (27º módulo) — Sprint 3 C19
# Roda diariamente às 07:00 (apos sync inicial e antes do horario comercial).
HEALTH_CHECK_CUSTEIO_ENABLED = os.environ.get("HEALTH_CHECK_CUSTEIO_ENABLED", "true").lower() == "true"
HEALTH_CHECK_CUSTEIO_HOUR = int(os.environ.get("HEALTH_CHECK_CUSTEIO_HOUR", "7"))
_ultimo_health_check_custeio = None  # Timestamp do ultimo health check bem-sucedido

# Eval Gate (28º módulo) — REMOVIDO (estrategia R2, 2026-06-12): A3 aposentado
# (2026-06-03, EXECUCAO.md); AGENT_EVAL_GATE era default-false e OFF em PROD —
# o modulo nunca atuou. eval_runner/eval_gate_service deletados; a funcao pura
# eval_gate migrou para app/agente/services/regression_gate.py (promocao A4).
# A numeracao dos modulos 29-33 foi PRESERVADA.

# Judge Enqueuer (29º módulo) — Onda 1 / E2, report-only, flag-OFF por default
# REUSA a flag AGENT_STEP_JUDGE (mesma que controla o job judge_step em shadow).
# Roda POR CICLO (cada tick de 30min), SEM guard temporal — varre steps recentes
# sem veredito e enfileira judge_step na fila LEVE 'agent_judge'.
# DEFAULT false: modulo e' no-op. Ativar em deploy.
JUDGE_ENQUEUER_ENABLED = os.environ.get("AGENT_STEP_JUDGE", "false").lower() == "true"
JUDGE_ENQUEUER_LOOKBACK_HOURS = int(os.environ.get("JUDGE_ENQUEUER_LOOKBACK_HOURS", "6"))
JUDGE_ENQUEUER_LIMIT = int(os.environ.get("JUDGE_ENQUEUER_LIMIT", "50"))

# Verify Enqueuer (30º módulo) — Onda 2 / B2, report-only, flag-OFF por default
# REUSA a flag AGENT_VERIFY (mesma que controla os verifiers shadow).
# Roda POR CICLO (cada tick de 30min), SEM guard temporal — varre steps recentes
# sem outcome_signal['verify'] e enfileira verify_step_shadow na fila LEVE
# 'agent_judge'. DEFAULT false: modulo e' no-op. Ativar em deploy.
VERIFY_ENQUEUER_ENABLED = os.environ.get("AGENT_VERIFY", "false").lower() == "true"
VERIFY_ENQUEUER_LOOKBACK_HOURS = int(os.environ.get("VERIFY_ENQUEUER_LOOKBACK_HOURS", "6"))
VERIFY_ENQUEUER_LIMIT = int(os.environ.get("VERIFY_ENQUEUER_LIMIT", "50"))

# Triage Enqueuer (31º módulo) — Tarefa 2c / B-TRIAGE, report-only, flag-OFF por default
# REUSA a flag AGENT_PLANNER (mesma que gateia o wiring de triage shadow).
# Roda POR CICLO (cada tick de 30min), SEM guard temporal — varre steps recentes
# sem outcome_signal['triage'] e enfileira triage_step_shadow na fila LEVE
# 'agent_judge'. DEFAULT false: modulo e' no-op. Ativar em deploy.
TRIAGE_ENQUEUER_ENABLED = os.environ.get("AGENT_PLANNER", "false").lower() == "true"
TRIAGE_ENQUEUER_LOOKBACK_HOURS = int(os.environ.get("TRIAGE_ENQUEUER_LOOKBACK_HOURS", "6"))
TRIAGE_ENQUEUER_LIMIT = int(os.environ.get("TRIAGE_ENQUEUER_LIMIT", "50"))

# Calibration Sampler (33º módulo) — Onda 1 / E3 (calibração do judge ONLINE),
# flag-OFF por default. Flag DEDICADA AGENT_CALIBRATION_SAMPLER (T4.5) — DESACOPLADA
# de AGENT_EVAL_CALIBRATION (que gateia o eval_runner/A3 LLM caro, APOSENTADO): ligar
# o sampler JAMAIS aciona um eval LLM caro. Roda POR CICLO (cada tick), INLINE (sem RQ)
# — leve: DB sweep + insert. Popula agent_eval_case a partir dos vereditos do online
# judge (substitui a fonte morta eval_runner/A3) p/ spot-check humano + concordance.
# DEFAULT false: modulo e' no-op. Ativar em deploy.
CALIBRATION_SAMPLER_ENABLED = os.environ.get("AGENT_CALIBRATION_SAMPLER", "false").lower() == "true"
CALIBRATION_SAMPLER_LOOKBACK_HOURS = int(os.environ.get("CALIBRATION_SAMPLER_LOOKBACK_HOURS", "24"))
CALIBRATION_SAMPLER_LIMIT = int(os.environ.get("CALIBRATION_SAMPLER_LIMIT", "200"))

# Directive Promotion (32º módulo) — Onda 3 / A4, flag-OFF por default
# Roda POR CICLO (cada tick), INLINE (sem RQ) — leve: DB sweep + scoring, zero LLM.
# DEFAULT false (flag AGENT_DIRECTIVE_PROMOTION): modulo e' no-op. Ativar em deploy.
from app.agente.config.feature_flags import (
    AGENT_DIRECTIVE_PROMOTION as DIRECTIVE_PROMOTION_ENABLED,
    AGENT_DIRECTIVE_LOOKBACK_HOURS as DIRECTIVE_LOOKBACK_HOURS,
    AGENT_DIRECTIVE_BATCH_LIMIT as DIRECTIVE_BATCH_LIMIT,
)

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
cte_cancelamento_outlook_job = None  # ✅ Job de Cancelamento CTe via Outlook 365 (step 18 — 2026-04-09)

# Flag para habilitar/desabilitar o step de cancelamento via Outlook (default: off)
CTE_CANCELAMENTO_ENABLED = os.environ.get('CTE_CANCELAMENTO_ENABLED', 'false').lower() == 'true'


def inicializar_services():
    """
    Inicializa os services FORA do contexto da aplicação.
    Isso evita problemas de SSL e contexto que ocorrem quando
    instanciados dentro do app.app_context()
    """
    global faturamento_service, carteira_service, requisicao_service, pedido_service, alocacao_service, entrada_material_service, cte_service, contas_receber_service, baixas_service, contas_pagar_service, nfd_service, pallet_service, reversao_service, monitoramento_sync_service, validacao_recebimento_job, validacao_ibscbs_job, extratos_service, picking_recebimento_sync_service, cte_cancelamento_outlook_job

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
        from app.fretes.jobs.cte_cancelamento_outlook_job import CteCancelamentoOutlookJob  # ✅ Job CTe Cancelamento Outlook (step 18)


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
        cte_cancelamento_outlook_job = CteCancelamentoOutlookJob()  # ✅ Instanciar job CTe Cancelamento Outlook (step 18)
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
    global faturamento_service, carteira_service, requisicao_service, pedido_service, alocacao_service, entrada_material_service, cte_service, contas_receber_service, baixas_service, contas_pagar_service, nfd_service, pallet_service, reversao_service, monitoramento_sync_service, validacao_recebimento_job, validacao_ibscbs_job, extratos_service, picking_recebimento_sync_service, cte_cancelamento_outlook_job, _ultima_reindexacao_embeddings, _ultima_varredura_seguranca, _ultimo_kg_cleanup, _ultima_auditoria_financeira, _ultimo_improvement_dialogue, _ultimo_fechamento_mes_custeio, _ultimo_health_check_custeio

    _t_inicio = time.time()
    logger.info("=" * 60)
    logger.info(f"🔄 SINCRONIZAÇÃO DEFINITIVA - {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info(f"⚙️ Configurações:")
    logger.info(f"   - Intervalo: {INTERVALO_MINUTOS} minutos")
    logger.info(f"   - Faturamento: status={STATUS_FATURAMENTO}min (48h)")
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
    logger.info(f"   - Pallets: janela={JANELA_PALLET}min (48h)")
    logger.info(f"   - Reversões NF: dias={DIAS_REVERSOES}")  # ✅ Adicionar Reversões ao log
    logger.info(f"   - Monitoramento Sync: automático")  # ✅ Adicionar Monitoramento ao log
    logger.info(f"   - Validação Recebimento (Fase 1+2): janela={JANELA_VALIDACAO_FISCAL}min")  # ✅ Validação de Recebimento (Fase 1 Fiscal + Fase 2 NF×PO)
    logger.info(f"   - Validação IBS/CBS (CTe+NF-e): janela={JANELA_VALIDACAO_FISCAL}min")  # ✅ Validação IBS/CBS
    logger.info(f"   - Extratos via Odoo: janela={JANELA_EXTRATOS}min")  # ✅ Sincronização de Extratos via Odoo
    logger.info(f"   - Pickings Recebimento: janela={JANELA_PICKINGS}min")  # ✅ Pickings Recebimento (Fase 4)
    logger.info(f"   - CTe Cancelamento Outlook: enabled={CTE_CANCELAMENTO_ENABLED}")  # ✅ Step 18
    logger.info("=" * 60)

    # Verificar se services estão inicializados
    if not all([faturamento_service, carteira_service, requisicao_service, pedido_service, alocacao_service, entrada_material_service, cte_service, contas_receber_service, baixas_service, contas_pagar_service, nfd_service, pallet_service, reversao_service, monitoramento_sync_service, validacao_recebimento_job, validacao_ibscbs_job, extratos_service, picking_recebimento_sync_service, cte_cancelamento_outlook_job]):
        logger.warning("⚠️ Services não inicializados, tentando inicializar...")
        if not inicializar_services():
            logger.error("❌ Falha ao inicializar services")
            return

    from app import create_app, db
    from sqlalchemy import text  # usado no REFRESH mv_pedidos
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
        _t_step = time.time()
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"💰 Sincronizando Faturamento (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Status: {STATUS_FATURAMENTO} minutos (48 horas)")

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

        logger.info(f"   [TIMER] Step 1 (Faturamento): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre os services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Carteira")
        except Exception as e:
            pass

        # 2️⃣ CARTEIRA - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 2 (Carteira): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Verificação de Exclusões")
        except Exception as e:
            pass

        # 2.5️⃣ VERIFICAÇÃO DE PEDIDOS EXCLUÍDOS DO ODOO - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 2.5 (Verificação Exclusões): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Requisições")
        except Exception as e:
            pass

        # 3️⃣ REQUISIÇÕES DE COMPRAS - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 3 (Requisições): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes dos Pedidos")
        except Exception as e:
            pass

        # 4️⃣ PEDIDOS DE COMPRAS - com retry
        _t_step = time.time()
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

        # 4️⃣.5️⃣ DETECTAR MUDANÇAS EM POs E MARCAR DFEs PARA REVALIDAÇÃO
        # Executa APÓS sync de Pedidos, ANTES das Alocações
        # Marca DFEs aprovados que usaram POs modificadas para revalidação
        try:
            from app.recebimento.services.po_changes_detector_service import PoChangesDetectorService

            logger.info("🔍 Detectando mudanças em POs para revalidação...")
            detector = PoChangesDetectorService()
            resultado_deteccao = detector.detectar_e_marcar_revalidacoes(
                minutos_janela=JANELA_PEDIDOS  # Mesma janela da sincronização de POs
            )
            logger.info(
                f"✅ POs verificadas: {resultado_deteccao.get('pos_verificadas', 0)}, "
                f"DFEs marcados para revalidação: {resultado_deteccao.get('dfes_marcados', 0)}"
            )
            db.session.commit()
        except Exception as e:
            logger.error(f"❌ Erro ao detectar mudanças em POs: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass

        # 4️⃣.6️⃣ AUTO-HEAL: backfill incremental de cnpj_fornecedor NULL em POs ativos
        # Sync por write_date nao detecta partner Odoo alterado APOS criacao do PO,
        # entao POs nascidos com partner sem CNPJ ficam stuck com cnpj_fornecedor=None.
        # Esses POs viram "sem_po" silencioso no match NF x PO (Fase 2).
        # Investigacao: agent_sessions.id=560 (Teams, 11/05/2026).
        # Roda a cada ciclo do scheduler em batch limitado (converge sem custo extra).
        try:
            logger.info("🔧 Auto-heal: backfill de POs com cnpj_fornecedor NULL...")
            resultado_backfill_cnpj = pedido_service.backfill_cnpj_via_odoo(limit=50)
            logger.info(
                f"✅ Auto-heal CNPJ: processados={resultado_backfill_cnpj.get('pos_distintos_processados', 0)}, "
                f"linhas_corrigidas={resultado_backfill_cnpj.get('linhas_corrigidas', 0)}, "
                f"partner_sem_cnpj={resultado_backfill_cnpj.get('pos_partner_sem_cnpj', 0)}"
            )
            db.session.commit()
        except Exception as e:
            logger.error(f"❌ Erro no auto-heal CNPJ: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass

        logger.info(f"   [TIMER] Step 4 (Pedidos + PO Changes + Auto-heal CNPJ): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Alocações")
        except Exception as e:
            pass

        # 5️⃣ ALOCAÇÕES DE COMPRAS - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 5 (Alocações): {time.time() - _t_step:.1f}s")

        # Limpar conexões antes de Entradas
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Entradas")
        except Exception as e:
            pass

        # 7️⃣ ENTRADAS DE MATERIAIS - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 6 (Entradas Materiais): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes dos CTes")
        except Exception as e:
            pass

        # 7️⃣ CTes - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 7 (CTes): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Contas a Receber")
        except Exception as e:
            pass

        # 8️⃣ CONTAS A RECEBER - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 8 (Contas a Receber): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Baixas")
        except Exception as e:
            pass

        # 9️⃣ BAIXAS/RECONCILIAÇÕES - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 9 (Baixas/Reconciliações): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Extratos via Odoo")
        except Exception as e:
            pass

        # 9️⃣.5️⃣ SINCRONIZAÇÃO COMPLETA DE EXTRATOS - IMPORTAÇÃO + SYNC + VINCULAÇÃO CNAB
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 9.5 (Extratos): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Contas a Pagar")
        except Exception as e:
            pass

        # 🔟 CONTAS A PAGAR - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 10 (Contas a Pagar): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das NFDs de Devolução")
        except Exception as e:
            pass

        # 1️⃣1️⃣ NFDs DE DEVOLUÇÃO - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 11 (NFDs Devolução): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes dos Pallets")
        except Exception as e:
            pass

        # 1️⃣2️⃣ PALLETS - com retry
        _t_step = time.time()
        sucesso_pallets = False
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"📦 Sincronizando Pallets (tentativa {tentativa}/{MAX_RETRIES})...")
                logger.info(f"   Janela: {JANELA_PALLET} minutos (48h)")

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
                    logger.info(f"   - NCs vinculadas: {resultado_pallets.get('ncs', {}).get('ncs_vinculadas', 0)}")
                    logger.info(f"   - Canceladas registradas: {resultado_pallets.get('canceladas', {}).get('canceladas_registradas', 0)}")
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

        logger.info(f"   [TIMER] Step 12 (Pallets): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes das Reversões de NF")
        except Exception as e:
            pass

        # 1️⃣3️⃣ REVERSÕES DE NF - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 13 (Reversões NF): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes do Sync Monitoramento")
        except Exception as e:
            pass

        # 1️⃣4️⃣ SYNC MONITORAMENTO - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 14 (Sync Monitoramento): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Validação Fiscal")
        except Exception as e:
            pass

        # 1️⃣5️⃣ VALIDAÇÃO DE RECEBIMENTO (FASE 1 + FASE 2) - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 15 (Validação Recebimento): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre jobs
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes da Validação IBS/CBS")
        except Exception as e:
            pass

        # 1️⃣6️⃣ VALIDAÇÃO IBS/CBS (CTes + NF-es) - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 16 (Validação IBS/CBS): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de Pickings Recebimento")
        except Exception as e:
            pass

        # 1️⃣7️⃣ PICKINGS RECEBIMENTO (Fase 4) - com retry
        _t_step = time.time()
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

        logger.info(f"   [TIMER] Step 17 (Pickings Recebimento): {time.time() - _t_step:.1f}s")

        # Limpar sessão entre services
        try:
            db.session.remove()
            db.engine.dispose()
            logger.info("♻️ Reconexão antes de CTe Cancelamento Outlook")
        except Exception:
            pass

        # 1️⃣8️⃣ CTE CANCELAMENTO OUTLOOK (2026-04-09) - feature-flag + retry
        # Processa XMLs de cancelamento de CTe vindos de pasta do Outlook 365
        # via Microsoft Graph API. Arquiva no Odoo (active=False) + cria
        # pendencias para revisao manual. Ver: .claude/plans/temporal-exploring-biscuit.md
        _t_step = time.time()
        sucesso_cte_cancelamento = True  # skip = sucesso (nao e erro)
        if CTE_CANCELAMENTO_ENABLED:
            sucesso_cte_cancelamento = False
            for tentativa in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(
                        f"📧 Processando CTes cancelados via Outlook "
                        f"(tentativa {tentativa}/{MAX_RETRIES})..."
                    )
                    with app.app_context():
                        resultado_cte_canc = cte_cancelamento_outlook_job.executar()

                    if resultado_cte_canc.get('sucesso'):
                        sucesso_cte_cancelamento = True
                        logger.info(
                            f"✅ CTe Cancelamento Outlook: "
                            f"{resultado_cte_canc.get('mensagem', '')}"
                        )
                        logger.info(
                            f"   - Pastas processadas: {resultado_cte_canc.get('pastas_processadas', 0)}"
                        )
                        logger.info(
                            f"   - Emails encontrados: {resultado_cte_canc.get('emails_encontrados', 0)}"
                        )
                        logger.info(
                            f"   - Duplicados (dedup): {resultado_cte_canc.get('emails_duplicados', 0)}"
                        )
                        logger.info(
                            f"   - Emails processados: {resultado_cte_canc.get('emails_processados', 0)}"
                        )
                        logger.info(
                            f"   - XMLs processados: {resultado_cte_canc.get('xmls_processados', 0)}"
                        )
                        logger.info(
                            f"   - XMLs ignorados (cteProc): {resultado_cte_canc.get('xmls_ignorados', 0)}"
                        )
                        logger.info(
                            f"   - Cancelados OK: {resultado_cte_canc.get('cancelados_ok', 0)}"
                        )
                        logger.info(
                            f"   - Pendencias: {resultado_cte_canc.get('pendencias', 0)}"
                        )
                        logger.info(
                            f"   - Erros: {resultado_cte_canc.get('erros', 0)}"
                        )
                        db.session.commit()
                        break
                    else:
                        logger.error(
                            f"❌ CTe Cancelamento Outlook falhou: "
                            f"{resultado_cte_canc.get('mensagem', 'erro desconhecido')}"
                        )
                        if tentativa < MAX_RETRIES:
                            logger.info(f"🔄 Aguardando {RETRY_DELAY}s...")
                            sleep(RETRY_DELAY)
                        else:
                            break

                except Exception as e:
                    logger.error(f"❌ Erro ao processar CTe Cancelamento Outlook: {e}")
                    if tentativa < MAX_RETRIES:
                        sleep(RETRY_DELAY)
                    else:
                        break
        else:
            logger.info(
                "ℹ️ CTe Cancelamento Outlook DESABILITADO "
                "(CTE_CANCELAMENTO_ENABLED=false)"
            )

        logger.info(
            f"   [TIMER] Step 18 (CTe Cancelamento Outlook): "
            f"{time.time() - _t_step:.1f}s"
        )

        # ── 2️⃣0️⃣ EMBEDDINGS REINDEXAÇÃO (diário, 20º módulo) ──
        _t_step = time.time()
        sucesso_embeddings = False
        embeddings_executou = False  # True = tentou rodar (hora certa + >24h)

        if EMBEDDINGS_REINDEX_ENABLED:
            hora_atual = agora_utc_naive().hour
            hoje = agora_utc_naive().date()

            deve_rodar = (
                hora_atual == EMBEDDINGS_REINDEX_HOUR
                and (_ultima_reindexacao_embeddings is None
                     or _ultima_reindexacao_embeddings.date() < hoje)
            )

            if deve_rodar:
                embeddings_executou = True

                # Cleanup antes (padrao do scheduler)
                try:
                    db.session.remove()
                    db.engine.dispose()
                    logger.info("♻️ Reconexão antes de Embeddings")
                except Exception:
                    pass

                try:
                    logger.info("🧠 Reindexação diária de embeddings...")
                    from app.scheduler.reindexacao_embeddings import executar_reindexacao_no_contexto

                    resultado_embeddings = executar_reindexacao_no_contexto()

                    if resultado_embeddings is not None:
                        erros_emb = sum(1 for v in resultado_embeddings.values() if 'error' in v)
                        if erros_emb == 0:
                            sucesso_embeddings = True
                            logger.info("✅ Embeddings reindexados com sucesso!")
                        else:
                            logger.warning(f"⚠️ Embeddings: {erros_emb} indexer(s) com erro")
                    else:
                        # EMBEDDINGS_ENABLED=false — ok, nao e falha
                        sucesso_embeddings = True
                        logger.info("   Embeddings desabilitado via EMBEDDINGS_ENABLED")

                    # Marcar como executado (mesmo com erros parciais, evita retry a cada 30min)
                    _ultima_reindexacao_embeddings = agora_utc_naive()

                except Exception as e:
                    logger.error(f"❌ Erro ao reindexar embeddings: {e}")
                    # Marcar como executado para nao retentar no proximo ciclo
                    _ultima_reindexacao_embeddings = agora_utc_naive()
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

        logger.info(f"   [TIMER] Step 20 (Embeddings): {time.time() - _t_step:.1f}s")

        # ── 2️⃣1️⃣ VARREDURA DE SEGURANÇA (diário, 21º módulo) ──
        _t_step = time.time()
        sucesso_seguranca = False
        seguranca_executou = False  # True = tentou rodar (hora certa + >24h)

        if SEGURANCA_SCAN_ENABLED:
            hora_atual_seg = agora_utc_naive().hour
            hoje_seg = agora_utc_naive().date()

            deve_rodar_seg = (
                hora_atual_seg == SEGURANCA_SCAN_HOUR
                and (_ultima_varredura_seguranca is None
                     or _ultima_varredura_seguranca.date() < hoje_seg)
            )

            if deve_rodar_seg:
                seguranca_executou = True

                # Verificar se auto_scan está habilitado na config do módulo
                scan_habilitado = True
                try:
                    from app.seguranca.models import SegurancaConfig
                    auto_scan = SegurancaConfig.get_valor('auto_scan_enabled')
                    if auto_scan is not None and str(auto_scan).lower() in ('false', '0', 'nao', 'não'):
                        scan_habilitado = False
                        logger.info("   Varredura de segurança desabilitada via config do módulo")
                except Exception:
                    pass  # Se módulo não existe ainda, pula silenciosamente

                if scan_habilitado:
                    # Cleanup antes (padrão do scheduler)
                    try:
                        db.session.remove()
                        db.engine.dispose()
                        logger.info("♻️ Reconexão antes de Varredura de Segurança")
                    except Exception:
                        pass

                    try:
                        logger.info("🛡️ Varredura diária de segurança...")
                        from app.seguranca.services.scan_orchestrator import executar_varredura

                        resultado_seguranca = executar_varredura(
                            tipo='FULL_SCAN',
                            disparado_por='scheduler'
                        )

                        if resultado_seguranca and resultado_seguranca.get('sucesso'):
                            sucesso_seguranca = True
                            total_vulns = resultado_seguranca.get('total_vulnerabilidades', 0)
                            logger.info(f"✅ Varredura de segurança concluída! Vulnerabilidades: {total_vulns}")
                        else:
                            erro_seg = resultado_seguranca.get('erro', 'Erro desconhecido') if resultado_seguranca else 'Sem resultado'
                            logger.warning(f"⚠️ Varredura de segurança: {erro_seg}")

                        _ultima_varredura_seguranca = agora_utc_naive()

                    except Exception as e:
                        logger.error(f"❌ Erro na varredura de segurança: {e}")
                        _ultima_varredura_seguranca = agora_utc_naive()
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
                else:
                    sucesso_seguranca = True  # Desabilitado não é falha
                    _ultima_varredura_seguranca = agora_utc_naive()

        logger.info(f"   [TIMER] Step 21 (Segurança): {time.time() - _t_step:.1f}s")

        # ── 2️⃣2️⃣ LIMPEZA KG ENTIDADES ÓRFÃS (semanal, 22º módulo) ──
        _t_step = time.time()
        sucesso_kg_cleanup = False
        kg_cleanup_executou = False

        if KG_CLEANUP_ENABLED:
            hora_kg = agora_utc_naive().hour
            dia_semana_kg = agora_utc_naive().weekday()
            hoje_kg = agora_utc_naive().date()

            deve_rodar_kg = (
                hora_kg == KG_CLEANUP_HOUR
                and dia_semana_kg == KG_CLEANUP_WEEKDAY
                and (_ultimo_kg_cleanup is None
                     or _ultimo_kg_cleanup.date() < hoje_kg)
            )

            if deve_rodar_kg:
                kg_cleanup_executou = True

                try:
                    db.session.remove()
                    db.engine.dispose()
                    logger.info("♻️ Reconexão antes de KG Cleanup")
                except Exception:
                    pass

                try:
                    logger.info("🧹 Limpeza semanal de entidades órfãs do Knowledge Graph...")
                    from app.agente.services.knowledge_graph_service import cleanup_orphan_entities

                    count = cleanup_orphan_entities(user_id=None)
                    sucesso_kg_cleanup = True
                    logger.info(f"[KG_CLEANUP] Removed {count} orphan entities")
                    _ultimo_kg_cleanup = agora_utc_naive()

                except Exception as e:
                    logger.error(f"❌ Erro no KG cleanup: {e}")
                    _ultimo_kg_cleanup = agora_utc_naive()
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

        logger.info(f"   [TIMER] Step 22 (KG Cleanup): {time.time() - _t_step:.1f}s")

        # ── 2️⃣3️⃣ AUDITORIA FINANCEIRA LOCAL × ODOO (diário, 23º módulo) ──
        _t_step = time.time()
        sucesso_auditoria_fin = False
        auditoria_fin_executou = False

        if AUDITORIA_FINANCEIRA_ENABLED:
            hora_aud = agora_utc_naive().hour
            hoje_aud = agora_utc_naive().date()

            deve_rodar_aud = (
                hora_aud == AUDITORIA_FINANCEIRA_HOUR
                and (_ultima_auditoria_financeira is None
                     or _ultima_auditoria_financeira.date() < hoje_aud)
            )

            if deve_rodar_aud:
                auditoria_fin_executou = True

                try:
                    db.session.remove()
                    db.engine.dispose()
                    logger.info("♻️ Reconexão antes de Auditoria Financeira")
                except Exception:
                    pass

                try:
                    logger.info("🔍 Auditoria diária de inconsistências financeiras Local × Odoo...")
                    from app.financeiro.workers.auditoria_inconsistencias_job import (
                        executar_auditoria_inconsistencias,
                        executar_auditoria_inconsistencias_pagar,
                    )

                    resultado_receber = executar_auditoria_inconsistencias(dry_run=False)
                    resultado_pagar = executar_auditoria_inconsistencias_pagar(dry_run=False)

                    erros_aud = (resultado_receber or {}).get('erros', 0) + (resultado_pagar or {}).get('erros', 0)
                    total_incons = (resultado_receber or {}).get('inconsistencias', 0) + (resultado_pagar or {}).get('inconsistencias', 0)

                    if erros_aud == 0:
                        sucesso_auditoria_fin = True
                        logger.info(f"✅ Auditoria financeira concluída! Inconsistências: {total_incons}")
                    else:
                        logger.warning(f"⚠️ Auditoria financeira: {erros_aud} erro(s)")

                    _ultima_auditoria_financeira = agora_utc_naive()

                except Exception as e:
                    logger.error(f"❌ Erro na auditoria financeira: {e}")
                    _ultima_auditoria_financeira = agora_utc_naive()
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

        logger.info(f"   [TIMER] Step 23 (Auditoria Financeira): {time.time() - _t_step:.1f}s")

        # ── 2️⃣4️⃣ REFRESH MATERIALIZED VIEWS COMERCIAIS (a cada ciclo) ──
        _t_step = time.time()
        try:
            db.session.remove()
            db.engine.dispose()
            from app.comercial.services.agregacao_service import refresh_materialized_views
            refresh_materialized_views()
        except Exception as e:
            logger.warning(f"⚠️ Refresh MV comerciais falhou (nao-critico): {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
        logger.info(f"   [TIMER] Step 24 (MV Comercial): {time.time() - _t_step:.1f}s")

        # ── 2️⃣4️⃣.5️⃣ REFRESH MV PEDIDOS (a cada ciclo) ──
        _t_step = time.time()
        try:
            db.session.remove()
            db.engine.dispose()
            db.session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pedidos"))
            db.session.commit()
            logger.info("   mv_pedidos refreshed OK")
        except Exception as e:
            # NAO e' "nao-critico": se o REFRESH falha, a MV CONGELA e a lista de
            # pedidos / contadores (counter_service usa PedidoMV) passam a servir
            # dados DESATUALIZADOS ate alguem resolver. Causa tipica: duplicata de
            # separacao_lote_id violando a UNIQUE idx_mv_pedidos_lote (ver migration
            # alterar_view_pedidos_v9_dedup_carvia — substring LIKE nas Partes CarVia).
            logger.error(f"❌ Refresh mv_pedidos FALHOU — MV ficara DESATUALIZADA "
                         f"(lista de pedidos servira dados defasados): {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
        logger.info(f"   [TIMER] Step 24.5 (MV Pedidos): {time.time() - _t_step:.1f}s")

        # ── 2️⃣5️⃣ IMPROVEMENT DIALOGUE BATCH (2x/dia, 25º módulo) ──
        _t_step = time.time()
        sucesso_improvement = False
        improvement_executou = False

        if IMPROVEMENT_DIALOGUE_ENABLED:
            hora_imp = agora_utc_naive().hour
            hoje_imp = agora_utc_naive().date()

            deve_rodar_imp = (
                hora_imp in IMPROVEMENT_DIALOGUE_HOURS
                and (_ultimo_improvement_dialogue is None
                     or _ultimo_improvement_dialogue < agora_utc_naive() - timedelta(hours=4))
            )

            if deve_rodar_imp:
                improvement_executou = True

                try:
                    db.session.remove()
                    db.engine.dispose()
                    logger.info("♻️ Reconexão antes de Improvement Dialogue")
                except Exception:
                    pass

                try:
                    logger.info("🔄 Improvement Dialogue batch (Agent SDK -> Claude Code)...")
                    from app.agente.services.improvement_suggester import executar_batch_improvement

                    resultado_imp = executar_batch_improvement(db)

                    sucesso_improvement = True
                    _ultimo_improvement_dialogue = agora_utc_naive()
                    logger.info(
                        f"✅ Improvement Dialogue: "
                        f"{resultado_imp.get('suggestions_created', 0)} sugestoes, "
                        f"{resultado_imp.get('evaluations_done', 0)} avaliacoes, "
                        f"{resultado_imp.get('sessions_analyzed', 0)} sessoes"
                    )

                except Exception as e:
                    logger.error(f"❌ Erro no Improvement Dialogue: {e}")
                    _ultimo_improvement_dialogue = agora_utc_naive()
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

        logger.info(f"   [TIMER] Step 25 (Improvement Dialogue): {time.time() - _t_step:.1f}s")

        # ── 2️⃣6️⃣ FECHAMENTO MENSAL DE CUSTEIO (mensal dia X, 26º módulo) ──
        # Sprint 2 C10: dispara fechar_mes do mes anterior. Idempotente (UNIQUE
        # em custo_mensal). Controle DUAL contra duplicacao:
        # 1. In-memory: _ultimo_fechamento_mes_custeio (rapido, mesmo processo)
        # 2. Persistido em DB: query CustoMensal status='FECHADO' do mes alvo
        #    (sobrevive restart do scheduler entre 04:00 e 04:30 do dia 5)
        # Guard de hora usa >= (nao ==) para nao perder o dia se scheduler
        # estiver down as 04:00 e voltar mais tarde no mesmo dia 5.
        _t_step = time.time()
        sucesso_fechar_mes_custeio = False
        fechar_mes_custeio_executou = False

        if FECHAR_MES_CUSTEIO_ENABLED:
            agora = agora_utc_naive()
            dia_atual = agora.day
            hora_atual_fmc = agora.hour
            chave_mes_atual = (agora.year, agora.month)

            # Guard 1: in-memory (rapido)
            deve_rodar_fmc = (
                dia_atual >= FECHAR_MES_CUSTEIO_DAY
                and hora_atual_fmc >= FECHAR_MES_CUSTEIO_HOUR
                and (_ultimo_fechamento_mes_custeio is None
                     or (_ultimo_fechamento_mes_custeio.year,
                         _ultimo_fechamento_mes_custeio.month) != chave_mes_atual)
            )

            # Guard 2: persistido em DB (sobrevive restart)
            # So consulta se passou no guard in-memory para evitar query desnecessaria
            if deve_rodar_fmc:
                try:
                    from datetime import timedelta as _td
                    from app.custeio.models import CustoMensal as _CM
                    # Mes alvo = mes anterior ao dia atual
                    primeiro_mes_atual = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    ultimo_mes_anterior = (primeiro_mes_atual - _td(days=1))
                    mes_alvo = ultimo_mes_anterior.month
                    ano_alvo = ultimo_mes_anterior.year

                    ja_fechado = _CM.query.filter_by(
                        mes=mes_alvo, ano=ano_alvo, status='FECHADO'
                    ).first()
                    if ja_fechado:
                        logger.info(
                            f"⏭️ Fechamento de {mes_alvo:02d}/{ano_alvo} ja realizado "
                            f"(custo_mensal tem registros FECHADO). Pulando step 26."
                        )
                        deve_rodar_fmc = False
                        # Sincronizar in-memory com DB para evitar consulta repetida
                        _ultimo_fechamento_mes_custeio = agora
                except Exception as e:
                    logger.warning(f"⚠️ Falha ao verificar custo_mensal existente: {e} (prosseguindo)")

            if deve_rodar_fmc:
                fechar_mes_custeio_executou = True

                # Cleanup antes (padrao do scheduler)
                try:
                    db.session.remove()
                    db.engine.dispose()
                    logger.info("♻️ Reconexão antes de Fechamento Mensal de Custeio")
                except Exception:
                    pass

                try:
                    logger.info("📅 Fechamento mensal automatico de custeio...")
                    from app.scheduler.fechar_mes_automatico import (
                        executar_fechamento_mes_anterior_no_contexto,
                    )
                    resultado_fmc = executar_fechamento_mes_anterior_no_contexto()

                    if resultado_fmc and not resultado_fmc.get('erro'):
                        sucesso_fechar_mes_custeio = True
                        logger.info(
                            f"✅ Fechamento de custeio concluido: "
                            f"{resultado_fmc.get('total', 0)} produtos"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Fechamento de custeio com problema: "
                            f"{resultado_fmc.get('erro') if resultado_fmc else 'sem retorno'}"
                        )

                    # Marcar como executado mesmo com erros parciais (evita retry no mesmo mes)
                    _ultimo_fechamento_mes_custeio = agora
                except Exception as e:
                    logger.error(f"❌ Erro no fechamento mensal de custeio: {e}")
                    _ultimo_fechamento_mes_custeio = agora
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

        logger.info(f"   [TIMER] Step 26 (Fechamento Custeio): {time.time() - _t_step:.1f}s")

        # ── 2️⃣7️⃣ HEALTH CHECK CUSTEIO (diário, 27º módulo) ──
        # Sprint 3 C19: verifica dormencia, produtos sem custo, regras vazias,
        # ACABADOS sem custo_producao, versoes duplicadas, parametros dormentes.
        _t_step = time.time()
        sucesso_health_custeio = False
        health_custeio_executou = False

        if HEALTH_CHECK_CUSTEIO_ENABLED:
            hora_atual_hc = agora_utc_naive().hour
            hoje_hc = agora_utc_naive().date()

            deve_rodar_hc = (
                hora_atual_hc == HEALTH_CHECK_CUSTEIO_HOUR
                and (_ultimo_health_check_custeio is None
                     or _ultimo_health_check_custeio.date() < hoje_hc)
            )

            if deve_rodar_hc:
                health_custeio_executou = True
                try:
                    db.session.remove()
                    db.engine.dispose()
                    logger.info("♻️ Reconexão antes de Health Check Custeio")
                except Exception:
                    pass

                try:
                    logger.info("🩺 Health check diario de custeio...")
                    from app.scheduler.health_check_custeio import (
                        executar_health_check_no_contexto,
                    )
                    resultado_hc = executar_health_check_no_contexto()

                    # OK se nao houver criticos (warnings sao informativos)
                    if resultado_hc and not resultado_hc.get('criticos'):
                        sucesso_health_custeio = True

                    _ultimo_health_check_custeio = agora_utc_naive()
                except Exception as e:
                    logger.error(f"❌ Erro no health check de custeio: {e}")
                    _ultimo_health_check_custeio = agora_utc_naive()
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

        logger.info(f"   [TIMER] Step 27 (Health Check Custeio): {time.time() - _t_step:.1f}s")

        # ── 2️⃣8️⃣ EVAL GATE — REMOVIDO (estrategia R2, 2026-06-12). A3 aposentado;
        # AGENT_EVAL_GATE era OFF em PROD e o modulo nunca atuou. Numeracao dos
        # modulos 29-33 preservada. ──

        # ── 2️⃣9️⃣ JUDGE ENQUEUER — varredor RQ do step_judge (29º módulo, report-only) ──
        # Onda 1 / E2. Flag AGENT_STEP_JUDGE default OFF → no-op.
        # Quando ON: varre AgentStep recentes (lookback) sem outcome_signal['judge']
        # e enfileira judge_step na fila LEVE 'agent_judge'. Roda TODO ciclo (sem
        # guard temporal) — cap por `limit` evita backlog. Best-effort: nunca falha o cron.
        _t_step = time.time()

        if JUDGE_ENQUEUER_ENABLED:
            try:
                from app.agente.workers.step_judge import enqueue_pending_judges

                _je_result = enqueue_pending_judges(
                    lookback_hours=JUDGE_ENQUEUER_LOOKBACK_HOURS,
                    limit=JUDGE_ENQUEUER_LIMIT,
                )
                logger.info(
                    f"[JUDGE_ENQUEUER] enfileirados={_je_result.get('enfileirados', 0)} "
                    f"candidatos={_je_result.get('candidatos', 0)}"
                )
            except Exception as e:
                logger.error(f"[JUDGE_ENQUEUER] Erro no modulo 29: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

        logger.info(f"   [TIMER] Step 29 (Judge Enqueuer): {time.time() - _t_step:.1f}s")

        # ── 3️⃣0️⃣ VERIFY ENQUEUER — varredor RQ do verify_step_shadow (30º módulo, report-only) ──
        # Onda 2 / B2. Flag AGENT_VERIFY default OFF → no-op.
        # Quando ON: varre AgentStep recentes (lookback) sem outcome_signal['verify']
        # e enfileira verify_step_shadow (3 verifiers: adversarial/arithmetic/domain)
        # na fila LEVE 'agent_judge'. Roda TODO ciclo (sem guard temporal) — cap por
        # `limit` evita backlog. Best-effort: nunca falha o cron. NÃO entra em modulos_sync.
        _t_step = time.time()

        if VERIFY_ENQUEUER_ENABLED:
            try:
                from app.agente.workers.plan_verifier import enqueue_pending_verifies

                _ve_result = enqueue_pending_verifies(
                    lookback_hours=VERIFY_ENQUEUER_LOOKBACK_HOURS,
                    limit=VERIFY_ENQUEUER_LIMIT,
                )
                logger.info(
                    f"[VERIFY_ENQUEUER] enfileirados={_ve_result.get('enfileirados', 0)} "
                    f"candidatos={_ve_result.get('candidatos', 0)}"
                )
            except Exception as e:
                logger.error(f"[VERIFY_ENQUEUER] Erro no modulo 30: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

        logger.info(f"   [TIMER] Step 30 (Verify Enqueuer): {time.time() - _t_step:.1f}s")

        # ── 3️⃣1️⃣ TRIAGE ENQUEUER — varredor RQ do triage_step_shadow (31º módulo, report-only) ──
        # Tarefa 2c / B-TRIAGE. Flag AGENT_PLANNER default OFF → no-op.
        # Quando ON: varre AgentStep recentes (lookback) sem outcome_signal['triage']
        # e enfileira triage_step_shadow (decompõe a meta do turno em steps ancorados
        # via triage_meta) na fila LEVE 'agent_judge'. Roda TODO ciclo (sem guard
        # temporal) — cap por `limit` evita backlog. Best-effort: nunca falha o cron.
        # NÃO entra em modulos_sync.
        _t_step = time.time()

        if TRIAGE_ENQUEUER_ENABLED:
            try:
                from app.agente.workers.triage_shadow import enqueue_pending_triages

                _te_result = enqueue_pending_triages(
                    lookback_hours=TRIAGE_ENQUEUER_LOOKBACK_HOURS,
                    limit=TRIAGE_ENQUEUER_LIMIT,
                )
                logger.info(
                    f"[TRIAGE_ENQUEUER] enfileirados={_te_result.get('enfileirados', 0)} "
                    f"candidatos={_te_result.get('candidatos', 0)}"
                )
            except Exception as e:
                logger.error(f"[TRIAGE_ENQUEUER] Erro no modulo 31: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

        logger.info(f"   [TIMER] Step 31 (Triage Enqueuer): {time.time() - _t_step:.1f}s")

        # ── 3️⃣2️⃣ DIRECTIVE PROMOTION — A4-batch (32º módulo, shadow/persist) ──
        # Onda 3 / A4. Flag AGENT_DIRECTIVE_PROMOTION default OFF → no-op.
        # Quando ON: varre AgentSessions recentes c/ plano 100% concluído → propõe
        # candidata → R9 anti-gaming DOMINA → gate vs floor → persiste directive_status='shadow'
        # (NUNCA injetada até ativação manual). Roda TODO ciclo (cap por limit).
        # Best-effort: nunca falha o cron. NÃO entra em modulos_sync.
        _t_step = time.time()

        if DIRECTIVE_PROMOTION_ENABLED:
            try:
                from app.agente.services.directive_promotion_service import run_directive_promotion_batch

                _dp_result = run_directive_promotion_batch(
                    lookback_hours=DIRECTIVE_LOOKBACK_HOURS,
                    limit=DIRECTIVE_BATCH_LIMIT,
                )
                logger.info(
                    f"[DIRECTIVE_PROMOTION] candidatos={_dp_result.get('candidatos', 0)} "
                    f"promovidos={_dp_result.get('promovidos', 0)} "
                    f"abstencoes={_dp_result.get('abstencoes', 0)} "
                    f"rejeitados={_dp_result.get('rejeitados', 0)}"
                )
            except Exception as e:
                logger.error(f"[DIRECTIVE_PROMOTION] Erro no modulo 32: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

        logger.info(f"   [TIMER] Step 32 (Directive Promotion): {time.time() - _t_step:.1f}s")

        # ── 3️⃣3️⃣ CALIBRATION SAMPLER — popula agent_eval_case do online judge (33º módulo) ──
        # Onda 1 / E3 (re-apontado pós-aposentadoria A3). Flag DEDICADA AGENT_CALIBRATION_SAMPLER
        # (T4.5, desacoplada do A3) default OFF → no-op.
        # Quando ON: varre AgentStep recentes (lookback) com outcome_signal['judge'] e
        # insere casos em agent_eval_case (dedup por step_uid) p/ spot-check humano +
        # concordance_rate. Prioriza discordância judge=success x adversarial.refuted (Task 3).
        # Roda TODO ciclo (cap por limit). Best-effort: nunca falha o cron. NÃO entra em modulos_sync.
        _t_step = time.time()

        if CALIBRATION_SAMPLER_ENABLED:
            try:
                from app.agente.workers.calibration_sampler import populate_calibration_cases

                _cs_result = populate_calibration_cases(
                    lookback_hours=CALIBRATION_SAMPLER_LOOKBACK_HOURS,
                    limit=CALIBRATION_SAMPLER_LIMIT,
                )
                logger.info(
                    f"[CALIBRATION_SAMPLER] inseridos={_cs_result.get('inseridos', 0)} "
                    f"candidatos={_cs_result.get('candidatos', 0)} "
                    f"prioritarios={_cs_result.get('prioritarios', 0)}"
                )
            except Exception as e:
                logger.error(f"[CALIBRATION_SAMPLER] Erro no modulo 33: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

        logger.info(f"   [TIMER] Step 33 (Calibration Sampler): {time.time() - _t_step:.1f}s")

        # Limpar conexões ao final
        try:
            db.session.remove()
            db.engine.dispose()
        except Exception as e:
            pass

        # Resumo final
        logger.info(f"   [TIMER] Duração TOTAL: {time.time() - _t_inicio:.1f}s ({(time.time() - _t_inicio)/60:.1f}min)")
        logger.info("=" * 60)

        modulos_sync = [sucesso_faturamento, sucesso_carteira, sucesso_verificacao, sucesso_requisicoes, sucesso_pedidos, sucesso_alocacoes, sucesso_entradas, sucesso_ctes, sucesso_contas_receber, sucesso_baixas, sucesso_extratos, sucesso_contas_pagar, sucesso_nfds, sucesso_pallets, sucesso_reversoes, sucesso_monitoramento, sucesso_validacao_recebimento, sucesso_validacao_ibscbs, sucesso_pickings_recebimento, sucesso_cte_cancelamento]

        if embeddings_executou:
            modulos_sync.append(sucesso_embeddings)

        if seguranca_executou:
            modulos_sync.append(sucesso_seguranca)

        if kg_cleanup_executou:
            modulos_sync.append(sucesso_kg_cleanup)

        if auditoria_fin_executou:
            modulos_sync.append(sucesso_auditoria_fin)

        if improvement_executou:
            modulos_sync.append(sucesso_improvement)

        if fechar_mes_custeio_executou:
            modulos_sync.append(sucesso_fechar_mes_custeio)

        if health_custeio_executou:
            modulos_sync.append(sucesso_health_custeio)

        # Modulo 28 (EVAL GATE) foi removido (estrategia R2, 2026-06-12)

        total_modulos = len(modulos_sync)
        total_sucesso = sum(modulos_sync)

        if total_sucesso == total_modulos:
            logger.info(f"✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO! ({total_modulos}/{total_modulos})")
        elif total_sucesso >= total_modulos - 2:
            logger.info(f"⚠️ Sincronização parcial - {total_sucesso}/{total_modulos} módulos OK")
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
            if CTE_CANCELAMENTO_ENABLED and not sucesso_cte_cancelamento:
                logger.info("   ❌ CTe Cancelamento Outlook (Step 18): FALHOU")
            if embeddings_executou and not sucesso_embeddings:
                logger.info("   ❌ Embeddings Reindexação: FALHOU")
            if seguranca_executou and not sucesso_seguranca:
                logger.info("   ❌ Varredura Segurança: FALHOU")
            if kg_cleanup_executou and not sucesso_kg_cleanup:
                logger.info("   ❌ KG Cleanup Entidades Órfãs: FALHOU")
        else:
            logger.error(f"❌ Sincronização com falhas graves - apenas {total_sucesso}/{total_modulos} módulos OK")
        logger.info("=" * 60)

        # ── REGISTRAR SCHEDULER HEALTH ──
        duracao_total_ms = int((time.time() - _t_inicio) * 1000)
        try:
            from app.scheduler.health_service import registrar_step
            # Steps core (sempre executam)
            _steps_info = [
                (1, 'Faturamento', sucesso_faturamento),
                (2, 'Carteira', sucesso_carteira),
                (3, 'Verificacao Exclusoes', sucesso_verificacao),
                (4, 'Requisicoes', sucesso_requisicoes),
                (5, 'Pedidos', sucesso_pedidos),
                (6, 'Alocacoes', sucesso_alocacoes),
                (7, 'Entradas Materiais', sucesso_entradas),
                (8, 'CTes', sucesso_ctes),
                (9, 'Contas Receber', sucesso_contas_receber),
                (10, 'Baixas Reconciliacoes', sucesso_baixas),
                (11, 'Extratos Odoo', sucesso_extratos),
                (12, 'Contas Pagar', sucesso_contas_pagar),
                (13, 'NFDs Devolucao', sucesso_nfds),
                (14, 'Pallets', sucesso_pallets),
                (15, 'Reversoes NF', sucesso_reversoes),
                (16, 'Monitoramento', sucesso_monitoramento),
                (17, 'Pickings Recebimento', sucesso_pickings_recebimento),
                (18, 'CTe Cancelamento Outlook', sucesso_cte_cancelamento),
            ]
            for step_num, step_name, sucesso in _steps_info:
                registrar_step(step_name, step_num, sucesso)

            # Steps diarios/semanais (registrar apenas se executaram)
            if embeddings_executou:
                registrar_step('Embeddings', 20, sucesso_embeddings)
            if seguranca_executou:
                registrar_step('Seguranca', 21, sucesso_seguranca)
            if kg_cleanup_executou:
                registrar_step('KG Cleanup', 22, sucesso_kg_cleanup)
            if auditoria_fin_executou:
                registrar_step('Auditoria Financeira', 23, sucesso_auditoria_fin)
            if improvement_executou:
                registrar_step('Improvement Dialogue', 25, sucesso_improvement)
            if fechar_mes_custeio_executou:
                registrar_step('Fechamento Mensal Custeio', 26, sucesso_fechar_mes_custeio)
            if health_custeio_executou:
                registrar_step('Health Check Custeio', 27, sucesso_health_custeio)

            # Resumo geral
            registrar_step('CICLO_COMPLETO', 0, total_sucesso == total_modulos,
                           duracao_ms=duracao_total_ms,
                           detalhes=f'{total_sucesso}/{total_modulos} OK')
        except Exception as e:
            logger.warning(f"Falha ao registrar scheduler health: {e}")


def executar_inicial():
    """
    Execução inicial com janelas maiores para recuperação pós-deploy
    """
    global JANELA_CARTEIRA

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


def executar_reconciliacao_teams():
    """Job periodico: re-entrega respostas do Teams que nunca chegaram ao usuario.

    Root cause: a Azure Function `frete-bot-func` esta no plano Consumption
    (sku Dynamic, alwaysOn=false) e escala a zero -> o POST /api/notify do
    backend leva `Connection refused` transitorio em cold-start, deixando tasks
    `completed` com `delivered_via IS NULL`. Esta varredura re-tenta a entrega
    (a function ja foi 'cutucada'/esquentou). Best-effort, NUNCA derruba o
    scheduler. Idempotente (claim atomico em delivered_via).

    Segue o padrao de `executar_sincronizacao`: cria app por execucao + dispose
    de conexoes (Render derruba SSL idle apos ~30-40s).
    """
    try:
        from app import create_app, db
        from app.teams.proactive import reconciliar_entregas_pendentes
        app = create_app()
        with app.app_context():
            try:
                db.session.close()
                db.engine.dispose()
            except Exception:
                pass
            res = reconciliar_entregas_pendentes()
            if res.get("candidatas"):
                logger.info(f"🔁 [TEAMS-RECONCILE] {res}")
    except Exception as e:
        logger.error(f"❌ [TEAMS-RECONCILE] job falhou: {e}", exc_info=True)


def executar_faturamento_diario_teams():
    """Job (seg-sex 6h): envia a imagem do faturamento do mes corrente no Teams.

    Gera o PNG (dias do mes + total do mes) a partir do Odoo (empresas CD+FB,
    somente vendas, notas lancadas), sobe no S3 e entrega na conversa 1:1 do
    destinatario via a mesma ponte proativa do bot. Best-effort, NUNCA derruba
    o scheduler. Atras da flag FATURAMENTO_DIARIO_TEAMS_ENABLED.

    Segue o padrao de `executar_reconciliacao_teams`: cria app por execucao +
    dispose de conexoes (Render derruba SSL idle).
    """
    try:
        from app import create_app, db
        from app.faturamento.services.faturamento_diario_teams_service import (
            enviar_faturamento_diario_teams,
        )
        app = create_app()
        with app.app_context():
            try:
                db.session.close()
                db.engine.dispose()
            except Exception:
                pass
            res = enviar_faturamento_diario_teams()
            logger.info(f"📊 [FAT-DIARIO] {res}")
    except Exception as e:
        logger.error(f"❌ [FAT-DIARIO] job falhou: {e}", exc_info=True)


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

    # Reconciliador de entregas Teams (2026-06-12): re-entrega tasks finais
    # orfas (delivered_via NULL) quando a Azure Function (Consumption/cold-start)
    # recusou o POST /api/notify. Best-effort, isolado (try/except no job).
    _teams_recon_min = int(os.getenv("TEAMS_RECONCILE_INTERVAL_MIN", "2"))
    scheduler.add_job(
        func=executar_reconciliacao_teams,
        trigger="interval",
        minutes=_teams_recon_min,
        id="teams_reconcile_entregas",
        name="Reconciliação de entregas Teams (órfãs delivered_via NULL)",
        max_instances=1,
        misfire_grace_time=120,
        replace_existing=True
    )
    logger.info(f"   8. Reconciliação Teams: a cada {_teams_recon_min} min (re-entrega órfãs)")

    # Faturamento diario no Teams (seg-sex): imagem do mes corrente + total
    # enviada proativamente ao destinatario (Marcus). Default OFF ate validar
    # em producao (flag FATURAMENTO_DIARIO_TEAMS_ENABLED).
    if os.getenv("FATURAMENTO_DIARIO_TEAMS_ENABLED", "false").lower() in ("1", "true", "yes", "on"):
        _fat_hour = int(os.getenv("FATURAMENTO_DIARIO_TEAMS_HOUR", "6"))
        scheduler.add_job(
            func=executar_faturamento_diario_teams,
            trigger="cron",
            day_of_week="mon-fri",
            hour=_fat_hour,
            minute=0,
            id="faturamento_diario_teams",
            name="Faturamento diario no Teams (seg-sex)",
            max_instances=1,
            misfire_grace_time=3600,
            replace_existing=True,
        )
        logger.info(f"   9. Faturamento diário Teams: seg-sex às {_fat_hour:02d}:00 (ENABLED)")
    else:
        logger.info("   9. Faturamento diário Teams: DESABILITADO (FATURAMENTO_DIARIO_TEAMS_ENABLED=false)")

    logger.info("=" * 60)
    logger.info("✅ Scheduler configurado com TODAS as correções:")
    logger.info("   1. Valores de janela corretos para cada serviço")
    logger.info("   2. Services instanciados FORA do contexto")
    logger.info("   3. Tratamento robusto de erros e reconexão")
    logger.info(f"   4. Embeddings: 20º módulo, diário às {EMBEDDINGS_REINDEX_HOUR:02d}:00 (enabled={EMBEDDINGS_REINDEX_ENABLED})")
    logger.info(f"   5. Segurança: 21º módulo, diário às {SEGURANCA_SCAN_HOUR:02d}:00 (enabled={SEGURANCA_SCAN_ENABLED})")
    logger.info(f"   6. Fechamento Custeio: 26º módulo, mensal dia {FECHAR_MES_CUSTEIO_DAY} às {FECHAR_MES_CUSTEIO_HOUR:02d}:00 (enabled={FECHAR_MES_CUSTEIO_ENABLED})")
    logger.info(f"   7. Health Check Custeio: 27º módulo, diário às {HEALTH_CHECK_CUSTEIO_HOUR:02d}:00 (enabled={HEALTH_CHECK_CUSTEIO_ENABLED})")
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