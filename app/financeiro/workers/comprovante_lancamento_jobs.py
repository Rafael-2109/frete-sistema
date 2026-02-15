# -*- coding: utf-8 -*-
"""
Jobs assíncronos para lançamento de comprovantes no Odoo
========================================================

Executados via Redis Queue na fila 'default'.

Fluxo:
1. Usuário clica "Lançar Todos Confirmados" na tela de comprovantes
2. Rota gera batch_id e enfileira job
3. Worker processa cada lançamento CONFIRMADO com commit individual
4. Progresso armazenado no Redis para polling em tempo real
5. Frontend exibe barra de progresso

Timeout: 60 minutos (chamadas XML-RPC ao Odoo podem ser lentas)

TRATAMENTO DE ERROS:
- Erro em lançamento 1 NÃO afeta processamento dos demais
- Cada lançamento tem commit isolado
- Circuit Breaker protege contra Odoo indisponível
"""

import json
import logging
import traceback
from app.utils.timezone import agora_utc_naive
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Timeout para batch completo (60 minutos)
TIMEOUT_LANCAMENTO_BATCH = 3600


# ========================================
# PROGRESSO EM TEMPO REAL VIA REDIS
# ========================================

def _get_redis_connection():
    """Obtém conexão Redis do RQ."""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


def _atualizar_progresso_lancamento(batch_id: str, progresso: dict):
    """
    Atualiza progresso do lançamento no Redis.

    Estrutura do progresso:
    {
        'batch_id': str,
        'status': 'processando' | 'concluido' | 'erro',
        'total': int,
        'processados': int,
        'sucesso': int,
        'erros': int,
        'ultimo_payment': str,
        'ultimo_update': str,
        'iniciado_em': str,
        'concluido_em': str | None,
        'estatisticas': dict | None,
        'detalhes': list | None,
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = agora_utc_naive().isoformat()
            key = f'comprovante_lancamento_progresso:{batch_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso lancamento: {e}")


def obter_progresso_lancamento(batch_id: str) -> Optional[dict]:
    """Obtém progresso do lançamento do Redis."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'comprovante_lancamento_progresso:{batch_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Erro ao obter progresso lancamento: {e}")
    return None


# ========================================
# CONTEXT MANAGER SEGURO
# ========================================

from app.financeiro.workers.utils import app_context_safe as _app_context_safe


# ========================================
# JOB PRINCIPAL: LANÇAMENTO BATCH
# ========================================

def processar_lancamento_comprovantes_job(
    batch_id: str,
    lancamento_ids: Optional[List[int]],
    usuario: str,
) -> Dict[str, Any]:
    """
    Processa lançamento de comprovantes confirmados no Odoo de forma assíncrona.

    Cada lançamento é processado ISOLADAMENTE:
    - Commit separado por lançamento
    - Erro em um não afeta os demais
    - Progresso atualizado no Redis após cada lançamento

    Args:
        batch_id: UUID do batch
        lancamento_ids: IDs específicos ou None para todos CONFIRMADOS
        usuario: Nome do usuário que iniciou

    Returns:
        Dict com resultado consolidado
    """
    logger.info(f"[Lancamento Batch] Iniciando - batch_id: {batch_id}")
    logger.info(f"[Lancamento Batch] IDs: {lancamento_ids or 'todos confirmados'}")
    logger.info(f"[Lancamento Batch] Usuário: {usuario}")

    # Inicializar progresso
    progresso = {
        'batch_id': batch_id,
        'status': 'processando',
        'total': 0,
        'processados': 0,
        'sucesso': 0,
        'erros': 0,
        'ultimo_payment': None,
        'iniciado_em': agora_utc_naive().isoformat(),
        'concluido_em': None,
        'estatisticas': None,
        'detalhes': [],
    }
    _atualizar_progresso_lancamento(batch_id, progresso)

    resultado = {
        'success': False,
        'batch_id': batch_id,
        'estatisticas': None,
        'erro_geral': None,
    }

    try:
        with _app_context_safe():
            from app.financeiro.services.comprovante_lancamento_service import (
                ComprovanteLancamentoService,
            )

            service = ComprovanteLancamentoService()

            def callback_progresso(processados, total, ultimo_resultado):
                """Callback chamado após cada lançamento processado."""
                progresso['processados'] = processados
                progresso['total'] = total
                progresso['sucesso'] = service.estatisticas['sucesso']
                progresso['erros'] = service.estatisticas['erros']
                progresso['ultimo_payment'] = ultimo_resultado.get('payment_name', '')
                _atualizar_progresso_lancamento(batch_id, progresso)

            # Executar lançamento batch
            res = service.lancar_batch(
                lancamento_ids=lancamento_ids,
                usuario=usuario,
                callback_progresso=callback_progresso,
            )

            resultado['success'] = res.get('sucesso', False)
            resultado['estatisticas'] = res.get('estatisticas')

            # Marcar como concluído
            progresso['status'] = 'concluido'
            progresso['concluido_em'] = agora_utc_naive().isoformat()
            progresso['estatisticas'] = res.get('estatisticas')
            progresso['detalhes'] = res.get('detalhes', [])

    except Exception as e:
        logger.error(f"[Lancamento Batch] Erro geral: {e}")
        logger.error(traceback.format_exc())

        resultado['erro_geral'] = str(e)
        progresso['status'] = 'erro'
        progresso['concluido_em'] = agora_utc_naive().isoformat()
        progresso['ultimo_payment'] = f"ERRO: {str(e)}"

    _atualizar_progresso_lancamento(batch_id, progresso)

    logger.info(
        f"[Lancamento Batch] Concluído - batch_id: {batch_id} | "
        f"Stats: {resultado.get('estatisticas')}"
    )

    return resultado
