# -*- coding: utf-8 -*-
"""
Jobs assincronos para conciliacao de extrato no Odoo
=====================================================

Executados via Redis Queue na fila 'default'.

Fluxo:
1. Usuario seleciona itens e solicita conciliacao via interface
2. Job enfileirado na fila
3. Worker processa: concilia cada item no Odoo (XML-RPC)
4. Progresso atualizado no Redis a cada item (polling pelo frontend)
5. Estatisticas dos lotes atualizadas ao final

Timeout: 1800 segundos (30 minutos) para lotes grandes
Cada item leva ~5-7s (8-15 chamadas XML-RPC ao Odoo)

TRATAMENTO DE ERROS:
- Per-item commit: item que falha nao afeta os demais
- Lock anti-duplicacao: impede re-submit dos mesmos itens
- Progresso em tempo real: usuario acompanha via polling
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional, List
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Timeout para lote completo (30 minutos)
TIMEOUT_CONCILIACAO_LOTE = 1800


# ========================================
# REDIS CONNECTION
# ========================================

def _get_redis_connection():
    """Obtem conexao Redis do RQ."""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


# ========================================
# LOCK PARA EVITAR DUPLICACAO DE JOBS
# ========================================

def _criar_lock_conciliacao(item_ids: List[int], job_id: str, ttl: int = 1800) -> bool:
    """
    Cria lock no Redis para evitar processamento duplicado dos mesmos itens.

    Args:
        item_ids: Lista de IDs de ExtratoItem a processar
        job_id: ID do job que esta adquirindo o lock
        ttl: Tempo de vida do lock em segundos (default: 30 minutos)

    Returns:
        True se lock criado com sucesso, False se ja existe lock ativo
    """
    try:
        redis_conn = _get_redis_connection()
        if not redis_conn:
            logger.warning("[Lock Conciliacao] Redis nao disponivel, prosseguindo sem lock")
            return True

        locks_criados = []
        for item_id in item_ids:
            lock_key = f'extrato_conciliacao_lock:{item_id}'

            # SET NX = apenas se nao existe
            resultado = redis_conn.set(lock_key, job_id, nx=True, ex=ttl)

            if resultado:
                locks_criados.append(item_id)
            else:
                dono_lock = redis_conn.get(lock_key)
                if dono_lock:
                    dono_lock = dono_lock.decode('utf-8') if isinstance(dono_lock, bytes) else dono_lock
                    if dono_lock != job_id:
                        logger.warning(
                            f"[Lock Conciliacao] Item {item_id} ja esta sendo "
                            f"processado pelo job {dono_lock}"
                        )
                        # Reverter locks criados
                        for criado_id in locks_criados:
                            redis_conn.delete(f'extrato_conciliacao_lock:{criado_id}')
                        return False

        logger.info(f"[Lock Conciliacao] Locks criados para {len(locks_criados)} itens (Job: {job_id})")
        return True

    except Exception as e:
        logger.error(f"[Lock Conciliacao] Erro ao criar lock: {e}")
        return True  # Em caso de erro, prosseguir


def _liberar_lock_conciliacao(item_ids: List[int], job_id: str):
    """
    Libera locks dos itens apos processamento.
    Apenas libera se o lock pertence ao job atual.
    """
    try:
        redis_conn = _get_redis_connection()
        if not redis_conn:
            return

        liberados = 0
        for item_id in item_ids:
            lock_key = f'extrato_conciliacao_lock:{item_id}'
            dono_lock = redis_conn.get(lock_key)
            if dono_lock:
                dono_lock = dono_lock.decode('utf-8') if isinstance(dono_lock, bytes) else dono_lock
                if dono_lock == job_id:
                    redis_conn.delete(lock_key)
                    liberados += 1

        logger.info(f"[Lock Conciliacao] Liberados {liberados} locks (Job: {job_id})")

    except Exception as e:
        logger.error(f"[Lock Conciliacao] Erro ao liberar locks: {e}")


# ========================================
# PROGRESSO EM TEMPO REAL VIA REDIS
# ========================================

def _atualizar_progresso(job_id: str, progresso: dict):
    """
    Atualiza progresso da conciliacao no Redis para acompanhamento em tempo real.

    Estrutura do progresso:
    {
        'job_id': str,
        'status': 'processando' | 'concluido' | 'concluido_com_erros' | 'erro' | 'bloqueado',
        'total_itens': int,
        'itens_processados': int,
        'itens_sucesso': int,
        'itens_erro': int,
        'item_atual': str,
        'ultimo_update': str,
        'detalhes': [...]
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = agora_utc_naive().isoformat()
            key = f'extrato_conciliacao_progresso:{job_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
            logger.debug(f"[Conciliacao] Progresso atualizado: {progresso.get('item_atual', 'N/A')}")
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso da conciliacao: {e}")


def obter_progresso(job_id: str) -> Optional[dict]:
    """Obtem progresso da conciliacao do Redis."""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'extrato_conciliacao_progresso:{job_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Erro ao obter progresso da conciliacao: {e}")
    return None


# ========================================
# CONTEXT MANAGER SEGURO
# ========================================

from app.financeiro.workers.utils import app_context_safe as _app_context_safe


# ========================================
# JOB STATUS (via RQ)
# ========================================

def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Obtem status de um job pelo ID.

    Returns:
        dict com status do job (status, status_display, created_at, etc.)
    """
    from rq.job import Job
    from app.portal.workers import get_redis_connection

    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)

        status_map = {
            'queued': 'Na fila',
            'started': 'Em processamento',
            'finished': 'Concluido',
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
        }

        # Calcular tempo de execucao se disponivel
        # RQ armazena started_at/ended_at como UTC aware
        if job.started_at and job.ended_at:
            result['duracao_segundos'] = (job.ended_at - job.started_at).total_seconds()
        elif job.started_at:
            from datetime import datetime as dt_cls, timezone
            result['duracao_segundos'] = (dt_cls.now(timezone.utc) - job.started_at).total_seconds()

        return result

    except Exception as e:
        return {
            'job_id': job_id,
            'status': 'not_found',
            'status_display': 'Nao encontrado',
            'error': str(e)
        }


# ========================================
# JOB PRINCIPAL: PROCESSAR CONCILIACAO
# ========================================

def processar_conciliacao_extrato_job(
    item_ids: List[int],
    usuario_nome: str
) -> Dict[str, Any]:
    """
    Job RQ para conciliacao de extrato.

    Fluxo:
    1. Criar locks anti-duplicacao
    2. Instanciar ExtratoConciliacaoService
    3. Loop por item com try/except + per-item commit
    4. Atualizar progresso no Redis a cada item
    5. Atualizar stats dos lotes afetados
    6. Liberar locks

    Args:
        item_ids: Lista de IDs de ExtratoItem a conciliar
        usuario_nome: Nome do usuario que solicitou

    Returns:
        dict: {success, total, conciliados, erros, detalhes, tempo_segundos}
    """
    from rq import get_current_job

    inicio = agora_utc_naive()

    current_job = get_current_job()
    job_id = current_job.id if current_job else None

    logger.info(
        f"[Job Conciliacao] Iniciando conciliacao de {len(item_ids)} itens "
        f"(Job ID: {job_id}, Usuario: {usuario_nome})"
    )

    resultado = {
        'success': False,
        'total_itens': len(item_ids),
        'conciliados': 0,
        'erros': 0,
        'detalhes': [],
        'erros_detalhe': [],
        'tempo_segundos': 0,
        'error': None,
        'usuario': usuario_nome
    }

    # Progresso inicial
    progresso = {
        'job_id': job_id,
        'status': 'processando',
        'total_itens': len(item_ids),
        'itens_processados': 0,
        'itens_sucesso': 0,
        'itens_erro': 0,
        'item_atual': 'Iniciando...',
        'inicio': agora_utc_naive().isoformat(),
        'detalhes': []
    }

    if job_id:
        _atualizar_progresso(job_id, progresso)

    # Tentar criar locks
    if job_id and not _criar_lock_conciliacao(item_ids, job_id):
        resultado['error'] = 'Itens ja estao sendo processados por outro job'
        resultado['success'] = False
        logger.warning("[Job Conciliacao] Lock falhou - itens ja em processamento")

        if job_id:
            progresso['status'] = 'bloqueado'
            progresso['item_atual'] = 'Itens ja em processamento por outro job'
            _atualizar_progresso(job_id, progresso)

        return resultado

    try:
        with _app_context_safe():
            from app import db
            from app.financeiro.models import ExtratoItem, ExtratoLote
            from app.financeiro.services.extrato_conciliacao_service import ExtratoConciliacaoService

            # Buscar itens validos
            itens = ExtratoItem.query.filter(
                ExtratoItem.id.in_(item_ids),
                ExtratoItem.aprovado == True,
                ExtratoItem.status != 'CONCILIADO'
            ).all()

            if not itens:
                resultado['error'] = 'Nenhum item valido encontrado para conciliar'
                resultado['success'] = False
                logger.warning(f"[Job Conciliacao] {resultado['error']}")
                if job_id:
                    progresso['status'] = 'concluido'
                    progresso['item_atual'] = resultado['error']
                    _atualizar_progresso(job_id, progresso)
                return resultado

            resultado['total_itens'] = len(itens)
            progresso['total_itens'] = len(itens)

            # Instanciar servico (reutiliza conexao Odoo)
            service = ExtratoConciliacaoService()

            # Processar cada item
            for idx, item in enumerate(itens):
                item_inicio = agora_utc_naive()
                item_resultado = {
                    'item_id': item.id,
                    'nome_pagador': item.nome_pagador or '',
                    'valor': float(item.valor) if item.valor else 0,
                    'success': False,
                    'message': '',
                    'tempo_segundos': 0
                }

                # Atualizar progresso
                label = item.nome_pagador or f'Item #{item.id}'
                progresso['item_atual'] = f"{label} ({idx + 1}/{len(itens)})"
                progresso['itens_processados'] = idx
                if job_id:
                    _atualizar_progresso(job_id, progresso)

                try:
                    logger.info(
                        f"[Job Conciliacao] Processando item {idx + 1}/{len(itens)}: "
                        f"ID {item.id} ({item.nome_pagador})"
                    )

                    service.conciliar_item(item)
                    db.session.commit()

                    item_resultado['success'] = True
                    item_resultado['message'] = 'Conciliado com sucesso'
                    resultado['conciliados'] += 1
                    progresso['itens_sucesso'] += 1

                    logger.info(f"[Job Conciliacao] Item {item.id} conciliado com sucesso")

                except Exception as e:
                    db.session.rollback()
                    item.status = 'ERRO'
                    item.mensagem = str(e)
                    db.session.commit()

                    item_resultado['success'] = False
                    item_resultado['message'] = str(e)
                    resultado['erros'] += 1
                    resultado['erros_detalhe'].append({'id': item.id, 'erro': str(e)})
                    progresso['itens_erro'] += 1

                    logger.error(f"[Job Conciliacao] Erro no item {item.id}: {e}")

                # Tempo do item
                item_resultado['tempo_segundos'] = (agora_utc_naive() - item_inicio).total_seconds()
                resultado['detalhes'].append(item_resultado)
                progresso['detalhes'].append(item_resultado)

            # =========================================================
            # Atualizar estatisticas dos lotes afetados
            # (mesma logica que existia na rota sincrona, linhas 241-256)
            # =========================================================
            from sqlalchemy import func

            lote_ids_afetados = set(item.lote_id for item in itens)
            for lote_id in lote_ids_afetados:
                lote = db.session.get(ExtratoLote, lote_id)
                if lote:
                    conciliados_count = db.session.query(func.count()).filter(
                        ExtratoItem.lote_id == lote_id,
                        ExtratoItem.status == 'CONCILIADO'
                    ).scalar()
                    lote.linhas_conciliadas = conciliados_count
                    if conciliados_count >= lote.total_linhas:
                        lote.status = 'CONCLUIDO'
                        lote.processado_em = agora_utc_naive()
                        lote.processado_por = usuario_nome
            db.session.commit()

            # Finalizar
            tempo_total = (agora_utc_naive() - inicio).total_seconds()
            resultado['tempo_segundos'] = tempo_total
            resultado['success'] = resultado['erros'] == 0

            # Progresso final
            progresso['status'] = 'concluido' if resultado['erros'] == 0 else 'concluido_com_erros'
            progresso['itens_processados'] = len(itens)
            progresso['item_atual'] = 'Concluido!'
            progresso['fim'] = agora_utc_naive().isoformat()
            progresso['tempo_segundos'] = tempo_total
            progresso['conciliados'] = resultado['conciliados']
            progresso['erros_total'] = resultado['erros']

            if job_id:
                _atualizar_progresso(job_id, progresso)
                _liberar_lock_conciliacao(item_ids, job_id)

            logger.info(
                f"[Job Conciliacao] Concluido em {tempo_total:.1f}s - "
                f"Sucesso: {resultado['conciliados']}, Erro: {resultado['erros']}"
            )

            return resultado

    except Exception as e:
        tempo_total = (agora_utc_naive() - inicio).total_seconds()
        resultado['tempo_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['success'] = False

        logger.error(f"[Job Conciliacao] Erro geral: {e}")
        logger.error(traceback.format_exc())

        if job_id:
            progresso['status'] = 'erro'
            progresso['item_atual'] = f'Erro: {str(e)[:100]}'
            progresso['fim'] = agora_utc_naive().isoformat()
            _atualizar_progresso(job_id, progresso)
            _liberar_lock_conciliacao(item_ids, job_id)

        return resultado
