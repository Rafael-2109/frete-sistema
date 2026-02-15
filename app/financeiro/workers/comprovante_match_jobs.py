# -*- coding: utf-8 -*-
"""
Jobs assincronos para matching de comprovantes com faturas Odoo
===============================================================

Executados via Redis Queue na fila 'default'.

Fluxo:
1. Usuario clica "Executar Match" na tela de comprovantes
2. Rota gera batch_id e enfileira job
3. Worker processa cada comprovante com commit individual
4. Progresso armazenado no Redis para polling em tempo real
5. Frontend exibe barra de progresso

Timeout: 60 minutos (chamadas XML-RPC ao Odoo podem ser lentas)

TRATAMENTO DE ERROS:
- Erro em comprovante 1 NAO afeta processamento dos demais
- Cada comprovante tem commit isolado
- Circuit Breaker protege contra Odoo indisponivel
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Timeout para batch completo (60 minutos)
TIMEOUT_MATCH_BATCH = 3600


# ========================================
# PROGRESSO EM TEMPO REAL VIA REDIS
# ========================================

def _get_redis_connection():
    """Obtem conexao Redis do RQ."""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


def _atualizar_progresso_match(batch_id: str, progresso: dict):
    """
    Atualiza progresso do matching no Redis.

    Estrutura do progresso:
    {
        'batch_id': str,
        'status': 'processando' | 'concluido' | 'erro',
        'total': int,
        'processados': int,
        'com_match': int,
        'sem_match': int,
        'erros': int,
        'ultimo_doc': str,
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
            key = f'comprovante_match_progresso:{batch_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso match: {e}")


def obter_progresso_match(batch_id: str) -> Optional[dict]:
    """Obtem progresso do matching do Redis."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'comprovante_match_progresso:{batch_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Erro ao obter progresso match: {e}")
    return None


# ========================================
# CONTEXT MANAGER SEGURO
# ========================================

from app.financeiro.workers.utils import app_context_safe as _app_context_safe


# ========================================
# JOB PRINCIPAL: MATCHING BATCH
# ========================================

def processar_match_comprovantes_job(
    batch_id: str,
    comprovante_ids: Optional[List[int]],
    filtros: Optional[Dict],
    usuario: str,
) -> Dict[str, Any]:
    """
    Processa matching de comprovantes com faturas Odoo de forma assincrona.

    Cada comprovante e processado ISOLADAMENTE:
    - Commit separado por comprovante
    - Erro em um nao afeta os demais
    - Progresso atualizado no Redis apos cada comprovante

    Args:
        batch_id: UUID do batch
        comprovante_ids: IDs especificos ou None para todos pendentes
        filtros: Dict com data_inicio, data_fim (opcionais)
        usuario: Nome do usuario que iniciou

    Returns:
        Dict com resultado consolidado
    """
    logger.info(f"[Match Batch] Iniciando - batch_id: {batch_id}")
    logger.info(f"[Match Batch] IDs: {comprovante_ids or 'todos pendentes'}")
    logger.info(f"[Match Batch] Usuario: {usuario}")

    # Inicializar progresso
    progresso = {
        'batch_id': batch_id,
        'status': 'processando',
        'total': 0,
        'processados': 0,
        'com_match': 0,
        'sem_match': 0,
        'erros': 0,
        'ultimo_doc': None,
        'iniciado_em': agora_utc_naive().isoformat(),
        'concluido_em': None,
        'estatisticas': None,
        'detalhes': None,
    }
    _atualizar_progresso_match(batch_id, progresso)

    resultado = {
        'success': False,
        'batch_id': batch_id,
        'estatisticas': None,
        'erro_geral': None,
    }

    try:
        with _app_context_safe():
            from app.financeiro.services.comprovante_match_service import ComprovanteMatchService

            service = ComprovanteMatchService()

            def callback_progresso(processados, total, ultimo_resultado):
                """Callback chamado apos cada comprovante processado."""
                progresso['processados'] = processados
                progresso['total'] = total
                progresso['com_match'] = service.estatisticas['com_match']
                progresso['sem_match'] = service.estatisticas['sem_match']
                progresso['erros'] = service.estatisticas['erros']
                progresso['ultimo_doc'] = ultimo_resultado.get('numero_documento', '')
                _atualizar_progresso_match(batch_id, progresso)

            # Parsear filtros de data (vieram como string do JSON)
            filtros_parsed = None
            if filtros:
                filtros_parsed = {}
                if filtros.get('data_inicio'):
                    try:
                        filtros_parsed['data_inicio'] = datetime.strptime(
                            filtros['data_inicio'], '%Y-%m-%d'
                        ).date()
                    except (ValueError, TypeError):
                        pass
                if filtros.get('data_fim'):
                    try:
                        filtros_parsed['data_fim'] = datetime.strptime(
                            filtros['data_fim'], '%Y-%m-%d'
                        ).date()
                    except (ValueError, TypeError):
                        pass

            # Executar matching
            res = service.executar_matching_comprovantes(
                comprovante_ids=comprovante_ids,
                filtros=filtros_parsed if filtros_parsed else None,
                callback_progresso=callback_progresso,
            )

            resultado['success'] = res.get('sucesso', False)
            resultado['estatisticas'] = res.get('estatisticas')

            # Marcar como concluido
            progresso['status'] = 'concluido'
            progresso['concluido_em'] = agora_utc_naive().isoformat()
            progresso['estatisticas'] = res.get('estatisticas')

    except Exception as e:
        logger.error(f"[Match Batch] Erro geral: {e}")
        logger.error(traceback.format_exc())

        resultado['erro_geral'] = str(e)
        progresso['status'] = 'erro'
        progresso['concluido_em'] = agora_utc_naive().isoformat()
        progresso['ultimo_doc'] = f"ERRO: {str(e)}"

    _atualizar_progresso_match(batch_id, progresso)

    logger.info(
        f"[Match Batch] Concluido - batch_id: {batch_id} | "
        f"Stats: {resultado.get('estatisticas')}"
    )

    return resultado
