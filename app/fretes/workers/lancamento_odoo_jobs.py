"""
Jobs assíncronos para lançamento de CTes e Despesas no Odoo
============================================================

Executados via Redis Queue na fila 'odoo_lancamento'

Fluxo:
1. Usuário solicita lançamento via interface
2. Job enfileirado na fila 'odoo_lancamento'
3. Worker processa: executa as 16 etapas
4. Resultado armazenado e banco atualizado

Timeout: 600 segundos (10 minutos) por lançamento individual
Timeout Lote: 1800 segundos (30 minutos) para lotes

TRATAMENTO DE ERROS:
- CTe/Despesa já lançada: Retorna sucesso com aviso (skip)
- CTe não encontrado: Retorna erro específico
- DFe com status diferente: Retorna erro com status atual
- Erro de conexão: Retorna erro com retry sugerido
"""

import json
import logging
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from app.utils.timezone import agora_utc_naive
logger = logging.getLogger(__name__)

# Timeout para conexão com Odoo (10 minutos por lançamento)
TIMEOUT_LANCAMENTO = 600

# Status que indicam que já foi processado
STATUS_JA_LANCADO = ['LANCADO_ODOO']
STATUS_DFE_VALIDO = '04'  # Status PO no Odoo

# Mapeamento de status DFe para descrição
STATUS_DFE_MAP = {
    '01': 'Rascunho',
    '02': 'Sincronizado',
    '03': 'Ciência/Confirmado',
    '04': 'PO (Pronto)',
    '05': 'Rateio',
    '06': 'Concluído',
    '07': 'Rejeitado'
}

# ========================================
# PROGRESSO DE LOTE EM TEMPO REAL
# ========================================


def _get_redis_connection():
    """Obtém conexão Redis do RQ"""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


# ========================================
# LOCK DE RE-ENTRADA (anti duplo-clique)
# ========================================
# TTL do lock: cobre o timeout do job (600s) + margem para o polling da Etapa 6
# (action_gerar_po_dfe pode aguardar ate 600s). Se o worker morrer sem liberar,
# o lock expira sozinho e o lancamento pode ser retomado.
LANCAMENTO_LOCK_TTL = 900


def _adquirir_lock_lancamento(tipo: str, entidade_id: int) -> bool:
    """
    Adquire lock distribuido para impedir lancamento concorrente da MESMA
    entidade (frete/despesa) no Odoo.

    Protege contra duplo-clique no botao de lancamento: a Etapa 6
    (`action_gerar_po_dfe`) demora 60-90s+, e duas execucoes paralelas do mesmo
    item chamam a Etapa 6 antes de qualquer uma ter criado o PO — gerando POs +
    invoices duplicados. Espelha o padrao de
    `app/recebimento/workers/recebimento_lf_jobs.py:_adquirir_lock`.

    Args:
        tipo: 'frete' ou 'despesa'
        entidade_id: ID do frete ou da despesa

    Returns:
        True se o lock foi adquirido (pode prosseguir), False se ja existe outro
        job processando a mesma entidade. Fail-open: se o Redis estiver
        indisponivel, retorna True (nao bloqueia o lancamento).
    """
    try:
        redis_conn = _get_redis_connection()
        if not redis_conn:
            return True  # Sem Redis → fail-open
        lock_key = f'lancamento_{tipo}_lock:{entidade_id}'
        return bool(redis_conn.set(lock_key, '1', nx=True, ex=LANCAMENTO_LOCK_TTL))
    except Exception as e:
        logger.warning(f"⚠️ [Lock] Falha ao adquirir lock {tipo}#{entidade_id}: {e}")
        return True  # Se Redis falhar, permite prosseguir (fail-open)


def _liberar_lock_lancamento(tipo: str, entidade_id: int):
    """Libera o lock de lancamento apos o processamento (ou abort)."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            redis_conn.delete(f'lancamento_{tipo}_lock:{entidade_id}')
    except Exception as e:
        logger.warning(f"⚠️ [Lock] Falha ao liberar lock {tipo}#{entidade_id}: {e}")


def _atualizar_progresso_lote(fatura_id: int, progresso: dict):
    """
    Atualiza progresso do lote no Redis para acompanhamento em tempo real.

    Estrutura do progresso:
    {
        'fatura_id': int,
        'status': 'processando' | 'concluido' | 'erro',
        'total_fretes': int,
        'total_despesas': int,
        'fretes_processados': int,
        'despesas_processadas': int,
        'fretes_sucesso': int,
        'despesas_sucesso': int,
        'fretes_erro': int,
        'despesas_erro': int,
        'item_atual': str,  # "Frete #123 (1/4)" ou "Despesa #456 (2/3)"
        'item_atual_etapa': str,  # "Etapa 6/16"
        'ultimo_update': str,  # ISO timestamp
        'detalhes': [...]  # Lista de resultados de cada item
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = agora_utc_naive().isoformat()
            key = f'lote_progresso:{fatura_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
            logger.debug(f"📊 [Lote] Progresso atualizado: {progresso.get('item_atual', 'N/A')}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao atualizar progresso do lote: {e}")


def _obter_progresso_lote(fatura_id: int) -> Optional[dict]: # type: ignore
    """Obtém progresso do lote do Redis"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'lote_progresso:{fatura_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"⚠️ Erro ao obter progresso do lote: {e}")
    return None


def _limpar_progresso_lote(fatura_id: int): # type: ignore
    """Remove progresso do lote do Redis após conclusão"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'lote_progresso:{fatura_id}'
            redis_conn.delete(key)
    except Exception as e:
        logger.warning(f"⚠️ Erro ao limpar progresso do lote: {e}")


@contextmanager
def _app_context_safe():
    """
    Context manager seguro para execução no worker.

    IMPORTANTE: Verifica se já existe um contexto ativo (ex: chamado de dentro de outro job)
    para evitar criar contextos aninhados que podem causar travamentos.

    Uso:
        with _app_context_safe():
            # código que precisa de contexto Flask
    """
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

    from flask import has_app_context

    # ✅ Se já existe contexto ativo, apenas executa o código (não cria novo contexto)
    if has_app_context():
        logger.debug("📎 [Context] Reutilizando contexto Flask existente")
        yield
        return

    # Criar novo contexto apenas quando necessário
    from app import create_app
    app = create_app()
    logger.debug("🆕 [Context] Novo contexto Flask criado")

    with app.app_context():
        yield


def lancar_frete_job(
    frete_id: int,
    usuario_nome: str,
    usuario_ip: str = None,
    cte_chave: str = None,
    data_vencimento: str = None
) -> Dict[str, Any]:
    """
    Job para lançar frete no Odoo (16 etapas)

    Args:
        frete_id: ID do frete no sistema
        usuario_nome: Nome do usuário que solicitou
        usuario_ip: IP do usuário (opcional)
        cte_chave: Chave de acesso do CTe (44 dígitos) - OPCIONAL, busca automaticamente se não informado
        data_vencimento: Data de vencimento YYYY-MM-DD (opcional)

    Returns:
        dict: Resultado do processamento
            - success: bool
            - frete_id: int
            - message: str
            - dfe_id: int (se sucesso)
            - purchase_order_id: int (se sucesso)
            - invoice_id: int (se sucesso)
            - etapas_concluidas: int
            - error: str (se erro)
            - error_type: str (tipo do erro para tratamento)
            - skipped: bool (se foi pulado por já estar lançado)
    """
    inicio = datetime.now()
    logger.info(f"🚀 [Job Frete] Iniciando lançamento frete #{frete_id}")

    resultado = {
        'success': False,
        'frete_id': frete_id,
        'cte_chave': cte_chave,
        'message': '',
        'dfe_id': None,
        'purchase_order_id': None,
        'invoice_id': None,
        'etapas_concluidas': 0,
        'error': None,
        'error_type': None,
        'skipped': False,
        'tempo_segundos': 0
    }

    # ========================================
    # LOCK DE RE-ENTRADA (anti duplo-clique → POs/invoices duplicados)
    # ========================================
    if not _adquirir_lock_lancamento('frete', frete_id):
        resultado['skipped'] = True
        resultado['error'] = (
            f"Frete #{frete_id} já está sendo lançado por outro job (lock ativo). "
            "Aguarde a conclusão do lançamento em andamento."
        )
        resultado['error_type'] = 'LANCAMENTO_EM_ANDAMENTO'
        resultado['message'] = resultado['error']
        logger.warning(f"🔒 [Job Frete] {resultado['error']}")
        return resultado

    try:
        with _app_context_safe():
            from app.fretes.models import Frete, ConhecimentoTransporte
            from app.fretes.services import LancamentoOdooService

            # ========================================
            # VALIDAÇÃO 1: Frete existe?
            # ========================================
            from app import db
            frete = db.session.get(Frete,frete_id) if frete_id else None
            if not frete:
                resultado['error'] = f"Frete ID {frete_id} não encontrado"
                resultado['error_type'] = 'FRETE_NAO_ENCONTRADO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Frete] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 2: Já foi lançado?
            # ========================================
            if frete.status in STATUS_JA_LANCADO:
                resultado['success'] = True
                resultado['skipped'] = True
                resultado['message'] = f"Frete #{frete_id} já está lançado no Odoo"
                resultado['dfe_id'] = frete.odoo_dfe_id
                resultado['purchase_order_id'] = frete.odoo_purchase_order_id
                resultado['invoice_id'] = frete.odoo_invoice_id
                logger.info(f"⏭️ [Job Frete] {resultado['message']}")
                return resultado

            # ========================================
            # BUSCAR CTe - Automático se não informado
            # Prioridade: 1) Informado 2) Vinculado 3) Automático
            # ========================================
            cte = None

            if cte_chave:
                # CTe informado explicitamente
                cte = db.session.query(ConhecimentoTransporte).filter_by(chave_acesso=cte_chave).first()
                if cte:
                    logger.info(f"✅ [Job Frete] CTe informado: {cte.numero_cte}")
                else:
                    resultado['error'] = f"CTe informado não encontrado (chave: {cte_chave[:20]}...)"
                    resultado['error_type'] = 'CTE_NAO_ENCONTRADO'
                    resultado['message'] = resultado['error']
                    logger.error(f"❌ [Job Frete] {resultado['error']}")
                    return resultado
            else:
                # BUSCA AUTOMÁTICA
                logger.info(f"🔍 [Job Frete] Buscando CTe automaticamente...")

                # PRIORIDADE 1: CTe vinculado explicitamente
                if frete.frete_cte_id:
                    cte = frete.cte or db.session.get(ConhecimentoTransporte,frete.frete_cte_id) if frete.frete_cte_id else None
                    if cte:
                        cte_chave = cte.chave_acesso
                        logger.info(f"✅ [Job Frete] Usando CTe VINCULADO: {cte.numero_cte}")
                    else:
                        resultado['error'] = f"CTe vinculado ID {frete.frete_cte_id} não encontrado"
                        resultado['error_type'] = 'CTE_VINCULADO_NAO_ENCONTRADO'
                        resultado['message'] = resultado['error']
                        logger.error(f"❌ [Job Frete] {resultado['error']}")
                        return resultado

                # PRIORIDADE 2: CTe vinculado via backref (conhecimentos_transporte)
                # Só usa se tiver EXATAMENTE 1 CTe vinculado
                if not cte and frete.conhecimentos_transporte:
                    ctes_vinculados = [ct for ct in frete.conhecimentos_transporte if ct.ativo]
                    if len(ctes_vinculados) == 1:
                        cte = ctes_vinculados[0]
                        cte_chave = cte.chave_acesso
                        logger.info(f"✅ [Job Frete] Usando CTe vinculado (backref): {cte.numero_cte}")
                    elif len(ctes_vinculados) > 1:
                        # Múltiplos CTes vinculados - requer seleção manual via frete_cte_id
                        ctes_info = ', '.join([f"CTe {c.numero_cte}" for c in ctes_vinculados[:5]])
                        resultado['error'] = f"Múltiplos CTes vinculados ({len(ctes_vinculados)}): {ctes_info}. Selecione um CTe específico."
                        resultado['error_type'] = 'MULTIPLOS_CTES'
                        resultado['message'] = resultado['error']
                        logger.warning(f"⚠️ [Job Frete] {resultado['error']}")
                        return resultado

                # PRIORIDADE 3: Busca automática por NFs + CNPJ
                # Só usa se não tiver CTe vinculado E encontrar EXATAMENTE 1 CTe
                if not cte:
                    ctes_relacionados = frete.buscar_ctes_relacionados()

                    if not ctes_relacionados:
                        resultado['error'] = "Nenhum CTe relacionado encontrado. Vincule um CTe manualmente."
                        resultado['error_type'] = 'CTE_NAO_ENCONTRADO'
                        resultado['message'] = resultado['error']
                        logger.error(f"❌ [Job Frete] {resultado['error']}")
                        return resultado

                    if len(ctes_relacionados) == 1:
                        cte = ctes_relacionados[0]
                        cte_chave = cte.chave_acesso
                        logger.info(f"✅ [Job Frete] CTe automático: {cte.numero_cte}")
                    else:
                        # Múltiplos CTes encontrados - requer vinculação manual
                        ctes_info = ', '.join([f"CTe {c.numero_cte}" for c in ctes_relacionados[:5]])
                        resultado['error'] = f"Múltiplos CTes ({len(ctes_relacionados)}): {ctes_info}. Vincule manualmente."
                        resultado['error_type'] = 'MULTIPLOS_CTES'
                        resultado['message'] = resultado['error']
                        logger.warning(f"⚠️ [Job Frete] {resultado['error']}")
                        return resultado

            # Validar chave (44 dígitos)
            if not cte_chave or len(cte_chave) != 44:
                resultado['error'] = f"Chave CTe inválida ({len(cte_chave) if cte_chave else 0} dígitos)"
                resultado['error_type'] = 'CTE_CHAVE_INVALIDA'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Frete] {resultado['error']}")
                return resultado

            resultado['cte_chave'] = cte_chave

            # ========================================
            # EXECUTAR LANÇAMENTO
            # ========================================
            logger.info(f"📋 [Job Frete] Iniciando 16 etapas para frete #{frete_id}")

            # Converter data_vencimento se string
            vencimento = None
            if data_vencimento:
                if isinstance(data_vencimento, str):
                    vencimento = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
                else:
                    vencimento = data_vencimento

            service = LancamentoOdooService(
                usuario_nome=usuario_nome,
                usuario_ip=usuario_ip
            )

            result = service.lancar_frete_odoo(
                frete_id=frete_id,
                cte_chave=cte_chave,
                data_vencimento=vencimento
            )

            # Mapear resultado
            tempo_total = (datetime.now() - inicio).total_seconds()
            resultado['tempo_segundos'] = tempo_total
            resultado['success'] = result.get('sucesso', False)
            resultado['message'] = result.get('mensagem', '')
            resultado['dfe_id'] = result.get('dfe_id')
            resultado['purchase_order_id'] = result.get('purchase_order_id')
            resultado['invoice_id'] = result.get('invoice_id')
            resultado['etapas_concluidas'] = result.get('etapas_concluidas', 0)

            if not resultado['success']:
                resultado['error'] = result.get('erro', 'Erro desconhecido')
                resultado['error_type'] = _classificar_erro(resultado['error'])

            if resultado['success']:
                logger.info(f"✅ [Job Frete] Frete #{frete_id} lançado em {tempo_total:.1f}s")
            else:
                logger.error(f"❌ [Job Frete] Frete #{frete_id} falhou: {resultado['error']}")

            return resultado

    except Exception as e:
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['error_type'] = 'ERRO_INESPERADO'
        resultado['message'] = f'Erro inesperado: {str(e)}'
        logger.error(f"💥 [Job Frete] Erro inesperado frete #{frete_id}: {e}")
        logger.error(traceback.format_exc())
        return resultado
    finally:
        _liberar_lock_lancamento('frete', frete_id)


def lancar_despesa_job(
    despesa_id: int,
    usuario_nome: str,
    usuario_ip: str = None,
    data_vencimento: str = None
) -> Dict[str, Any]:
    """
    Job para lançar despesa extra no Odoo (16 etapas)

    Args:
        despesa_id: ID da despesa extra no sistema
        usuario_nome: Nome do usuário que solicitou
        usuario_ip: IP do usuário (opcional)
        data_vencimento: Data de vencimento YYYY-MM-DD (opcional)

    Returns:
        dict: Resultado do processamento (mesma estrutura de lancar_frete_job)
    """
    inicio = datetime.now()
    logger.info(f"🚀 [Job Despesa] Iniciando lançamento despesa #{despesa_id}")

    resultado = {
        'success': False,
        'despesa_id': despesa_id,
        'message': '',
        'dfe_id': None,
        'purchase_order_id': None,
        'invoice_id': None,
        'etapas_concluidas': 0,
        'error': None,
        'error_type': None,
        'skipped': False,
        'tempo_segundos': 0
    }

    # ========================================
    # LOCK DE RE-ENTRADA (anti duplo-clique → POs/invoices duplicados)
    # ========================================
    if not _adquirir_lock_lancamento('despesa', despesa_id):
        resultado['skipped'] = True
        resultado['error'] = (
            f"Despesa #{despesa_id} já está sendo lançada por outro job (lock ativo). "
            "Aguarde a conclusão do lançamento em andamento."
        )
        resultado['error_type'] = 'LANCAMENTO_EM_ANDAMENTO'
        resultado['message'] = resultado['error']
        logger.warning(f"🔒 [Job Despesa] {resultado['error']}")
        return resultado

    try:
        with _app_context_safe():
            from app.fretes.models import DespesaExtra
            from app.fretes.services.lancamento_despesa_odoo_service import LancamentoDespesaOdooService

            # ========================================
            # VALIDAÇÃO 1: Despesa existe?
            # ========================================
            from app import db
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
            if not despesa:
                resultado['error'] = f"Despesa Extra ID {despesa_id} não encontrada"
                resultado['error_type'] = 'DESPESA_NAO_ENCONTRADA'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 2: Já foi lançada?
            # ========================================
            if despesa.status in STATUS_JA_LANCADO:
                resultado['success'] = True
                resultado['skipped'] = True
                resultado['message'] = f"Despesa #{despesa_id} já está lançada no Odoo"
                resultado['dfe_id'] = despesa.odoo_dfe_id
                resultado['purchase_order_id'] = despesa.odoo_purchase_order_id
                resultado['invoice_id'] = despesa.odoo_invoice_id
                logger.info(f"⏭️ [Job Despesa] {resultado['message']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 3: Tem CTe vinculado?
            # ========================================
            if not despesa.despesa_cte_id:
                resultado['error'] = "Despesa não possui CTe Complementar vinculado"
                resultado['error_type'] = 'CTE_NAO_VINCULADO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 4: Tipo documento é CTe?
            # ========================================
            if not despesa.tipo_documento or despesa.tipo_documento.upper() != 'CTE':
                resultado['error'] = f"Tipo de documento '{despesa.tipo_documento}' não suportado para lançamento Odoo"
                resultado['error_type'] = 'TIPO_DOCUMENTO_INVALIDO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 5: Status permite lançamento?
            # ========================================
            if despesa.status != 'VINCULADO_CTE':
                resultado['error'] = f"Status '{despesa.status}' não permite lançamento. Esperado: VINCULADO_CTE"
                resultado['error_type'] = 'STATUS_INVALIDO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # EXECUTAR LANÇAMENTO
            # ========================================
            logger.info(f"📋 [Job Despesa] Iniciando 16 etapas para despesa #{despesa_id}")

            # Converter data_vencimento se string
            vencimento = None
            if data_vencimento:
                if isinstance(data_vencimento, str):
                    vencimento = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
                else:
                    vencimento = data_vencimento

            service = LancamentoDespesaOdooService(
                usuario_nome=usuario_nome,
                usuario_ip=usuario_ip
            )

            result = service.lancar_despesa_odoo(
                despesa_id=despesa_id,
                data_vencimento=vencimento
            )

            # Mapear resultado
            tempo_total = (datetime.now() - inicio).total_seconds()
            resultado['tempo_segundos'] = tempo_total
            resultado['success'] = result.get('sucesso', False)
            resultado['message'] = result.get('mensagem', '')
            resultado['dfe_id'] = result.get('dfe_id')
            resultado['purchase_order_id'] = result.get('purchase_order_id')
            resultado['invoice_id'] = result.get('invoice_id')
            resultado['etapas_concluidas'] = result.get('etapas_concluidas', 0)

            if not resultado['success']:
                resultado['error'] = result.get('erro', 'Erro desconhecido')
                resultado['error_type'] = _classificar_erro(resultado['error'])

            if resultado['success']:
                logger.info(f"✅ [Job Despesa] Despesa #{despesa_id} lançada em {tempo_total:.1f}s")
            else:
                logger.error(f"❌ [Job Despesa] Despesa #{despesa_id} falhou: {resultado['error']}")

            return resultado

    except Exception as e:
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['error_type'] = 'ERRO_INESPERADO'
        resultado['message'] = f'Erro inesperado: {str(e)}'
        logger.error(f"💥 [Job Despesa] Erro inesperado despesa #{despesa_id}: {e}")
        logger.error(traceback.format_exc())
        return resultado
    finally:
        _liberar_lock_lancamento('despesa', despesa_id)


def lancar_lote_job(
    fatura_frete_id: int,
    usuario_nome: str,
    usuario_ip: str = None,
    data_vencimento_fatura: str = None
) -> Dict[str, Any]:
    """
    Job para enfileirar lançamento de todos os fretes e despesas de uma fatura no Odoo.

    MUDANÇA: Agora usa ENQUEUE para cada item, em vez de chamar diretamente.
    Isso permite:
    - Cada item aparece na fila de auditoria individualmente
    - Se um travar, não afeta os outros
    - Mais visibilidade do progresso

    Args:
        fatura_frete_id: ID da fatura de frete
        usuario_nome: Nome do usuário que solicitou
        usuario_ip: IP do usuário (opcional)
        data_vencimento_fatura: Data de vencimento da fatura (YYYY-MM-DD)

    Returns:
        dict: Resultado com jobs_ids enfileirados
            - success: bool
            - fatura_frete_id: int
            - message: str
            - total_fretes: int
            - total_despesas: int
            - jobs_fretes: List[Dict] - IDs dos jobs enfileirados
            - jobs_despesas: List[Dict] - IDs dos jobs enfileirados
    """
    inicio = datetime.now()
    logger.info(f"🚀 [Job Lote] Enfileirando lançamentos da Fatura #{fatura_frete_id}")

    resultado = {
        'success': False,
        'fatura_frete_id': fatura_frete_id,
        'message': '',
        'total_fretes': 0,
        'total_despesas': 0,
        'jobs_fretes': [],
        'jobs_despesas': [],
        'tempo_total_segundos': 0
    }

    try:
        with _app_context_safe():
            from app.fretes.models import FaturaFrete, Frete, DespesaExtra
            from app.portal.workers import enqueue_job
            from app import db

            # ========================================
            # VALIDAÇÃO: Fatura existe?
            # ========================================
            fatura = db.session.get(FaturaFrete,fatura_frete_id) if fatura_frete_id else None
            if not fatura:
                resultado['error'] = f"Fatura de Frete ID {fatura_frete_id} não encontrada"
                resultado['error_type'] = 'FATURA_NAO_ENCONTRADA'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Lote] {resultado['error']}")
                return resultado

            # ========================================
            # BUSCAR FRETES DA FATURA (excluir já lançados)
            # ========================================
            fretes = db.session.query(Frete).filter_by(fatura_frete_id=fatura_frete_id).filter(
                Frete.status != 'LANCADO_ODOO'
            ).all()
            resultado['total_fretes'] = len(fretes)
            logger.info(f"📦 [Job Lote] Encontrados {len(fretes)} fretes pendentes na fatura")

            # ========================================
            # BUSCAR DESPESAS DA FATURA (excluir já lançadas)
            # ========================================
            despesas = db.session.query(DespesaExtra).filter_by(fatura_frete_id=fatura_frete_id).filter(
                DespesaExtra.status != 'LANCADO_ODOO'
            ).all()
            resultado['total_despesas'] = len(despesas)
            logger.info(f"📦 [Job Lote] Encontradas {len(despesas)} despesas pendentes na fatura")

            # ========================================
            # INICIALIZAR PROGRESSO EM TEMPO REAL
            # ========================================
            progresso = {
                'fatura_id': fatura_frete_id,
                'fatura_numero': fatura.numero_fatura,
                'transportadora': fatura.transportadora.razao_social if fatura.transportadora else 'N/A',
                'status': 'enfileirando',
                'total_fretes': len(fretes),
                'total_despesas': len(despesas),
                'jobs_enfileirados': 0,
                'item_atual': 'Enfileirando jobs...',
                'jobs': [],
                'inicio': agora_utc_naive().isoformat()
            }
            _atualizar_progresso_lote(fatura_frete_id, progresso)

            # ========================================
            # ENFILEIRAR FRETES
            # ========================================
            for idx, frete in enumerate(fretes):
                try:
                    logger.info(f"📋 [Job Lote] Enfileirando frete #{frete.id} ({idx + 1}/{len(fretes)})")

                    job = enqueue_job(
                        lancar_frete_job,
                        frete.id,
                        usuario_nome,
                        usuario_ip,
                        None,  # cte_chave - será buscado automaticamente
                        data_vencimento_fatura,
                        queue_name='odoo_lancamento',
                        timeout='10m'
                    )

                    job_info = {
                        'tipo': 'frete',
                        'id': frete.id,
                        'job_id': job.id,
                        'status': 'enfileirado'
                    }
                    resultado['jobs_fretes'].append(job_info)
                    progresso['jobs'].append(job_info)
                    progresso['jobs_enfileirados'] = len(resultado['jobs_fretes']) + len(resultado['jobs_despesas'])

                    logger.info(f"✅ [Job Lote] Frete #{frete.id} enfileirado - Job ID: {job.id}")

                except Exception as e:
                    logger.error(f"❌ [Job Lote] Erro ao enfileirar frete #{frete.id}: {e}")
                    resultado['jobs_fretes'].append({
                        'tipo': 'frete',
                        'id': frete.id,
                        'job_id': None,
                        'status': 'erro',
                        'error': str(e)
                    })

            # ========================================
            # ENFILEIRAR DESPESAS
            # ========================================
            for idx, despesa in enumerate(despesas):
                try:
                    logger.info(f"📋 [Job Lote] Enfileirando despesa #{despesa.id} ({idx + 1}/{len(despesas)})")

                    job = enqueue_job(
                        lancar_despesa_job,
                        despesa.id,
                        usuario_nome,
                        usuario_ip,
                        data_vencimento_fatura,
                        queue_name='odoo_lancamento',
                        timeout='10m'
                    )

                    job_info = {
                        'tipo': 'despesa',
                        'id': despesa.id,
                        'job_id': job.id,
                        'status': 'enfileirado'
                    }
                    resultado['jobs_despesas'].append(job_info)
                    progresso['jobs'].append(job_info)
                    progresso['jobs_enfileirados'] = len(resultado['jobs_fretes']) + len(resultado['jobs_despesas'])

                    logger.info(f"✅ [Job Lote] Despesa #{despesa.id} enfileirada - Job ID: {job.id}")

                except Exception as e:
                    logger.error(f"❌ [Job Lote] Erro ao enfileirar despesa #{despesa.id}: {e}")
                    resultado['jobs_despesas'].append({
                        'tipo': 'despesa',
                        'id': despesa.id,
                        'job_id': None,
                        'status': 'erro',
                        'error': str(e)
                    })

            # ========================================
            # RESUMO FINAL
            # ========================================
            tempo_total = (datetime.now() - inicio).total_seconds()
            resultado['tempo_total_segundos'] = tempo_total

            total_enfileirados = sum(1 for j in resultado['jobs_fretes'] if j.get('job_id')) + \
                                 sum(1 for j in resultado['jobs_despesas'] if j.get('job_id')) # type: ignore # noqa: E127
            total_erros = sum(1 for j in resultado['jobs_fretes'] if j.get('status') == 'erro') + \
                          sum(1 for j in resultado['jobs_despesas'] if j.get('status') == 'erro') # type: ignore # noqa: E127

            resultado['success'] = (total_erros == 0 and total_enfileirados > 0)

            resultado['message'] = (
                f"Lote enfileirado em {tempo_total:.1f}s! "
                f"{total_enfileirados} jobs na fila 'odoo_lancamento'. "
                f"Acompanhe na tela de auditoria."
            )
            logger.info(f"✅ [Job Lote] {resultado['message']}")

            # 📊 Finalizar progresso
            progresso['status'] = 'enfileirado'
            progresso['item_atual'] = 'Todos os jobs enfileirados!'
            progresso['fim'] = agora_utc_naive().isoformat()
            progresso['tempo_total_segundos'] = tempo_total
            _atualizar_progresso_lote(fatura_frete_id, progresso)

            return resultado

    except Exception as e:
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_total_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['error_type'] = 'ERRO_INESPERADO'
        resultado['message'] = f'Erro inesperado no lote: {str(e)}'
        logger.error(f"💥 [Job Lote] Erro inesperado fatura #{fatura_frete_id}: {e}")
        logger.error(traceback.format_exc())
        return resultado


def _classificar_erro(erro_msg: str) -> str:
    """
    Classifica o tipo de erro baseado na mensagem para facilitar tratamento

    Returns:
        Código do tipo de erro
    """
    erro_lower = erro_msg.lower() if erro_msg else ''

    if 'não encontrado' in erro_lower or 'not found' in erro_lower:
        if 'cte' in erro_lower or 'chave' in erro_lower:
            return 'CTE_NAO_ENCONTRADO'
        if 'dfe' in erro_lower:
            return 'DFE_NAO_ENCONTRADO'
        return 'REGISTRO_NAO_ENCONTRADO'

    if 'status' in erro_lower:
        if 'rascunho' in erro_lower or '01' in erro_lower:
            return 'DFE_STATUS_RASCUNHO'
        if 'confirmado' in erro_lower or 'ciência' in erro_lower or '03' in erro_lower:
            return 'DFE_STATUS_CONFIRMADO'
        if 'concluído' in erro_lower or '06' in erro_lower:
            return 'DFE_STATUS_CONCLUIDO'
        return 'DFE_STATUS_INVALIDO'

    if 'autenticação' in erro_lower or 'auth' in erro_lower:
        return 'ERRO_AUTENTICACAO'

    if 'timeout' in erro_lower or 'timed out' in erro_lower:
        return 'ERRO_TIMEOUT'

    if 'conexão' in erro_lower or 'connection' in erro_lower:
        return 'ERRO_CONEXAO'

    if 'permissão' in erro_lower or 'permission' in erro_lower or 'access' in erro_lower:
        return 'ERRO_PERMISSAO'

    if 'já lançado' in erro_lower or 'já está' in erro_lower:
        return 'JA_LANCADO'

    return 'ERRO_DESCONHECIDO'


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Obtém status de um job pelo ID

    Args:
        job_id: ID do job no Redis Queue

    Returns:
        dict com status do job
    """
    from rq.job import Job
    from app.portal.workers import get_redis_connection

    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)

        status_map = {
            'queued': 'Na fila',
            'started': 'Em processamento',
            'finished': 'Concluído',
            'failed': 'Falhou',
            'deferred': 'Adiado',
            'scheduled': 'Agendado',
            'stopped': 'Parado',
            'canceled': 'Cancelado'
        }

        result = {
            'job_id': job_id,
            'status': job.get_status(),
            'status_display': status_map.get(job.get_status(), job.get_status()),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
            'result': job.result if job.is_finished else None,
            'error': str(job.exc_info) if job.is_failed else None,
            'meta': job.meta
        }

        # Calcular tempo de execução se disponível
        if job.started_at and job.ended_at:
            result['duracao_segundos'] = (job.ended_at - job.started_at).total_seconds()
        elif job.started_at:
            result['duracao_segundos'] = (datetime.now(job.started_at.tzinfo) - job.started_at).total_seconds()

        return result

    except Exception as e:
        return {
            'job_id': job_id,
            'status': 'not_found',
            'status_display': 'Não encontrado',
            'error': str(e)
        }
