# -*- coding: utf-8 -*-
"""
Jobs assincronos para baixa de titulos no Odoo
==============================================

Executados via Redis Queue na fila 'default' ou 'high'

Fluxo:
1. Usuario solicita processamento via interface
2. Job enfileirado na fila
3. Worker processa: executa baixas no Odoo
4. Resultado armazenado e banco atualizado

Timeout: 600 segundos (10 minutos) por item individual
Timeout Lote: 1800 segundos (30 minutos) para lotes grandes

TRATAMENTO DE ERROS:
- Titulo nao encontrado: Retorna erro especifico
- Valor maior que saldo: Retorna erro com valores
- Duplicidade de desconto: Retorna erro com aviso
- Erro de conexao: Retorna erro com retry sugerido
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional, List
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Timeout para processamento de baixa (10 minutos por item)
TIMEOUT_BAIXA_ITEM = 600

# Timeout para lote completo (30 minutos)
TIMEOUT_BAIXA_LOTE = 1800


# ========================================
# LOCK PARA EVITAR DUPLICACAO DE JOBS
# ========================================


def _criar_lock_processamento(item_ids: List[int], job_id: str, ttl: int = 1800) -> bool:
    """
    Cria lock no Redis para evitar processamento duplicado dos mesmos itens.

    Args:
        item_ids: Lista de IDs de itens a processar
        job_id: ID do job que esta adquirindo o lock
        ttl: Tempo de vida do lock em segundos (default: 30 minutos)

    Returns:
        True se lock criado com sucesso, False se ja existe lock ativo
    """
    try:
        redis_conn = _get_redis_connection()
        if not redis_conn:
            logger.warning("[Lock] Redis nao disponivel, prosseguindo sem lock")
            return True

        # Criar locks individuais para cada item
        locks_criados = []
        for item_id in item_ids:
            lock_key = f'baixa_item_lock:{item_id}'

            # Tentar criar lock (SET NX = apenas se nao existe)
            resultado = redis_conn.set(lock_key, job_id, nx=True, ex=ttl)

            if resultado:
                locks_criados.append(item_id)
            else:
                # Lock ja existe - verificar quem tem o lock
                dono_lock = redis_conn.get(lock_key)
                if dono_lock:
                    dono_lock = dono_lock.decode('utf-8') if isinstance(dono_lock, bytes) else dono_lock
                    if dono_lock != job_id:
                        logger.warning(f"[Lock] Item {item_id} ja esta sendo processado pelo job {dono_lock}")
                        # Reverter locks criados
                        for criado_id in locks_criados:
                            redis_conn.delete(f'baixa_item_lock:{criado_id}')
                        return False

        logger.info(f"[Lock] Locks criados para {len(locks_criados)} itens (Job: {job_id})")
        return True

    except Exception as e:
        logger.error(f"[Lock] Erro ao criar lock: {e}")
        return True  # Em caso de erro, prosseguir


def _liberar_lock_processamento(item_ids: List[int], job_id: str):
    """
    Libera locks dos itens apos processamento.

    Apenas libera se o lock pertence ao job atual (evita liberar lock de outro job).
    """
    try:
        redis_conn = _get_redis_connection()
        if not redis_conn:
            return

        liberados = 0
        for item_id in item_ids:
            lock_key = f'baixa_item_lock:{item_id}'

            # Verificar se o lock pertence a este job antes de deletar
            dono_lock = redis_conn.get(lock_key)
            if dono_lock:
                dono_lock = dono_lock.decode('utf-8') if isinstance(dono_lock, bytes) else dono_lock
                if dono_lock == job_id:
                    redis_conn.delete(lock_key)
                    liberados += 1

        logger.info(f"[Lock] Liberados {liberados} locks (Job: {job_id})")

    except Exception as e:
        logger.error(f"[Lock] Erro ao liberar locks: {e}")


def _verificar_item_em_processamento(item_id: int, job_id: str) -> bool:
    """
    Verifica se um item especifico esta sendo processado por outro job.

    Returns:
        True se pode processar, False se outro job esta processando
    """
    try:
        redis_conn = _get_redis_connection()
        if not redis_conn:
            return True

        lock_key = f'baixa_item_lock:{item_id}'
        dono_lock = redis_conn.get(lock_key)

        if not dono_lock:
            return True

        dono_lock = dono_lock.decode('utf-8') if isinstance(dono_lock, bytes) else dono_lock
        return dono_lock == job_id

    except Exception:
        return True


# ========================================
# PROGRESSO EM TEMPO REAL VIA REDIS
# ========================================


def _get_redis_connection():
    """Obtem conexao Redis do RQ"""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


def _atualizar_progresso_baixa(job_id: str, progresso: dict):
    """
    Atualiza progresso da baixa no Redis para acompanhamento em tempo real.

    Estrutura do progresso:
    {
        'job_id': str,
        'tipo': 'item' | 'lote',
        'status': 'processando' | 'concluido' | 'erro',
        'total_itens': int,
        'itens_processados': int,
        'itens_sucesso': int,
        'itens_erro': int,
        'item_atual': str,  # "NF 12345 P1 (3/10)"
        'ultimo_update': str,  # ISO timestamp
        'detalhes': [...]  # Lista de resultados de cada item
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = agora_utc_naive().isoformat()
            key = f'baixa_progresso:{job_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
            logger.debug(f"[Baixa] Progresso atualizado: {progresso.get('item_atual', 'N/A')}")
    except Exception as e:
        logger.warning(f"Erro ao atualizar progresso da baixa: {e}")


def obter_progresso_baixa(job_id: str) -> Optional[dict]:
    """Obtem progresso da baixa do Redis"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'baixa_progresso:{job_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"Erro ao obter progresso da baixa: {e}")
    return None


def _limpar_progresso_baixa(job_id: str):
    """Remove progresso da baixa do Redis apos conclusao"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'baixa_progresso:{job_id}'
            redis_conn.delete(key)
    except Exception as e:
        logger.warning(f"Erro ao limpar progresso da baixa: {e}")


# ========================================
# CONTEXT MANAGER SEGURO
# ========================================

from app.financeiro.workers.utils import app_context_safe as _app_context_safe


# ========================================
# JOB: PROCESSAR ITENS SELECIONADOS
# ========================================


def processar_itens_baixa_job(
    item_ids: List[int],
    usuario_nome: str
) -> Dict[str, Any]:
    """
    Job para processar lista de itens de baixa selecionados.

    Args:
        item_ids: Lista de IDs de BaixaTituloItem a processar
        usuario_nome: Nome do usuario que solicitou

    Returns:
        dict: Resultado do processamento
            - success: bool
            - total_itens: int
            - itens_sucesso: int
            - itens_erro: int
            - detalhes: List[Dict] - resultado de cada item
            - tempo_segundos: float
            - error: str (se erro geral)
    """
    from rq import get_current_job

    inicio = agora_utc_naive()

    # Obter job_id do job atual
    current_job = get_current_job()
    job_id = current_job.id if current_job else None

    logger.info(f"[Job Baixa] Iniciando processamento de {len(item_ids)} itens (Job ID: {job_id})")

    resultado = {
        'success': False,
        'total_itens': len(item_ids),
        'itens_sucesso': 0,
        'itens_erro': 0,
        'itens_pulados': 0,
        'detalhes': [],
        'tempo_segundos': 0,
        'error': None,
        'usuario': usuario_nome
    }

    # Progresso inicial
    progresso = {
        'job_id': job_id,
        'tipo': 'lote',
        'status': 'processando',
        'total_itens': len(item_ids),
        'itens_processados': 0,
        'itens_sucesso': 0,
        'itens_erro': 0,
        'itens_pulados': 0,
        'item_atual': 'Iniciando...',
        'inicio': agora_utc_naive().isoformat(),
        'detalhes': []
    }

    if job_id:
        _atualizar_progresso_baixa(job_id, progresso)

    # Tentar criar locks para os itens
    if job_id and not _criar_lock_processamento(item_ids, job_id):
        resultado['error'] = 'Itens ja estao sendo processados por outro job'
        resultado['success'] = False
        logger.warning(f"[Job Baixa] Lock falhou - itens ja em processamento")

        if job_id:
            progresso['status'] = 'bloqueado'
            progresso['item_atual'] = 'Itens ja em processamento por outro job'
            _atualizar_progresso_baixa(job_id, progresso)

        return resultado

    try:
        with _app_context_safe():
            from app import db
            from app.financeiro.models import BaixaTituloItem
            from app.financeiro.services.baixa_titulos_service import BaixaTitulosService

            # Buscar itens
            itens = BaixaTituloItem.query.filter(
                BaixaTituloItem.id.in_(item_ids),
                BaixaTituloItem.ativo == True,
                BaixaTituloItem.status.in_(['PENDENTE', 'VALIDO', 'ERRO'])
            ).all()

            if not itens:
                resultado['error'] = 'Nenhum item valido encontrado para processar'
                resultado['success'] = False
                logger.warning(f"[Job Baixa] {resultado['error']}")
                return resultado

            resultado['total_itens'] = len(itens)
            progresso['total_itens'] = len(itens)

            # Instanciar servico (reutiliza conexao Odoo)
            service = BaixaTitulosService()

            # Processar cada item
            for idx, item in enumerate(itens):
                item_inicio = agora_utc_naive()
                item_resultado = {
                    'item_id': item.id,
                    'nf': item.nf_excel,
                    'parcela': item.parcela_excel,
                    'valor': item.valor_excel,
                    'success': False,
                    'message': '',
                    'payment_name': None,
                    'tempo_segundos': 0
                }

                # Atualizar progresso
                progresso['item_atual'] = f"NF {item.nf_excel} P{item.parcela_excel} ({idx + 1}/{len(itens)})"
                progresso['itens_processados'] = idx
                if job_id:
                    _atualizar_progresso_baixa(job_id, progresso)

                try:
                    # Verificar se este item especifico pode ser processado
                    if job_id and not _verificar_item_em_processamento(item.id, job_id):
                        logger.warning(f"[Job Baixa] Item {item.id} pulado - sendo processado por outro job")
                        item_resultado['success'] = False
                        item_resultado['message'] = 'Item pulado - sendo processado por outro job'
                        resultado['itens_pulados'] += 1
                        progresso['itens_pulados'] += 1
                        resultado['detalhes'].append(item_resultado)
                        progresso['detalhes'].append(item_resultado)
                        continue

                    logger.info(f"[Job Baixa] Processando item {idx + 1}/{len(itens)}: NF {item.nf_excel} P{item.parcela_excel}")

                    # Processar item via servico
                    service._processar_item(item)

                    # Sucesso - status ja foi atualizado pelo servico
                    item_resultado['success'] = True
                    item_resultado['message'] = 'Processado com sucesso'
                    item_resultado['payment_name'] = item.payment_odoo_name
                    resultado['itens_sucesso'] += 1
                    progresso['itens_sucesso'] += 1

                    logger.info(f"[Job Baixa] Item {item.id} processado com sucesso: {item.payment_odoo_name}")

                except Exception as e:
                    # Erro no item
                    item.status = 'ERRO'
                    item.mensagem = str(e)
                    item.processado_em = agora_utc_naive()

                    item_resultado['success'] = False
                    item_resultado['message'] = str(e)
                    resultado['itens_erro'] += 1
                    progresso['itens_erro'] += 1

                    logger.error(f"[Job Baixa] Erro no item {item.id}: {e}")

                # Commit apos cada item
                db.session.commit()

                # Tempo do item
                item_resultado['tempo_segundos'] = (agora_utc_naive() - item_inicio).total_seconds()
                resultado['detalhes'].append(item_resultado)
                progresso['detalhes'].append(item_resultado)

            # Finalizar
            tempo_total = (agora_utc_naive() - inicio).total_seconds()
            resultado['tempo_segundos'] = tempo_total
            resultado['success'] = resultado['itens_erro'] == 0

            # Progresso final
            progresso['status'] = 'concluido' if resultado['success'] else 'concluido_com_erros'
            progresso['itens_processados'] = len(itens)
            progresso['item_atual'] = 'Concluido!'
            progresso['fim'] = agora_utc_naive().isoformat()
            progresso['tempo_segundos'] = tempo_total

            if job_id:
                _atualizar_progresso_baixa(job_id, progresso)
                # Liberar locks apos processamento
                _liberar_lock_processamento(item_ids, job_id)

            logger.info(
                f"[Job Baixa] Concluido em {tempo_total:.1f}s - "
                f"Sucesso: {resultado['itens_sucesso']}, Erro: {resultado['itens_erro']}, Pulados: {resultado['itens_pulados']}"
            )

            return resultado

    except Exception as e:
        tempo_total = (agora_utc_naive() - inicio).total_seconds()
        resultado['tempo_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['success'] = False

        logger.error(f"[Job Baixa] Erro geral: {e}")
        logger.error(traceback.format_exc())

        # Progresso de erro
        if job_id:
            progresso['status'] = 'erro'
            progresso['item_atual'] = f'Erro: {str(e)[:100]}'
            progresso['fim'] = agora_utc_naive().isoformat()
            _atualizar_progresso_baixa(job_id, progresso)
            # Liberar locks mesmo em caso de erro
            _liberar_lock_processamento(item_ids, job_id)

        return resultado


# ========================================
# JOB: PROCESSAR LOTE COMPLETO
# ========================================


def processar_lote_baixa_job(
    lote_id: int,
    usuario_nome: str
) -> Dict[str, Any]:
    """
    Job para processar todas as baixas ativas de um lote.

    Args:
        lote_id: ID do BaixaTituloLote a processar
        usuario_nome: Nome do usuario que solicitou

    Returns:
        dict: Resultado do processamento
            - success: bool
            - lote_id: int
            - total_itens: int
            - itens_sucesso: int
            - itens_erro: int
            - tempo_segundos: float
            - error: str (se erro)
    """
    from rq import get_current_job

    inicio = agora_utc_naive()

    # Obter job_id do job atual
    current_job = get_current_job()
    job_id = current_job.id if current_job else None

    logger.info(f"[Job Baixa Lote] Iniciando processamento do lote {lote_id} (Job ID: {job_id})")

    resultado = {
        'success': False,
        'lote_id': lote_id,
        'total_itens': 0,
        'itens_sucesso': 0,
        'itens_erro': 0,
        'tempo_segundos': 0,
        'error': None,
        'usuario': usuario_nome
    }

    try:
        with _app_context_safe():
            from app import db
            from app.financeiro.models import BaixaTituloLote, BaixaTituloItem
            from app.financeiro.services.baixa_titulos_service import BaixaTitulosService

            # Buscar lote
            lote = db.session.get(BaixaTituloLote,lote_id) if lote_id else None
            if not lote:
                resultado['error'] = f'Lote {lote_id} nao encontrado'
                logger.error(f"[Job Baixa Lote] {resultado['error']}")
                return resultado

            # Verificar status
            if lote.status not in ['IMPORTADO', 'VALIDADO']:
                resultado['error'] = f'Lote nao pode ser processado (status: {lote.status})'
                logger.error(f"[Job Baixa Lote] {resultado['error']}")
                return resultado

            # Atualizar status do lote
            lote.status = 'PROCESSANDO'
            lote.processado_por = usuario_nome
            db.session.commit()

            # Buscar IDs dos itens ativos e validos
            itens = BaixaTituloItem.query.filter_by(
                lote_id=lote_id,
                ativo=True,
                status='VALIDO'
            ).all()

            if not itens:
                lote.status = 'CONCLUIDO'
                lote.processado_em = agora_utc_naive()
                db.session.commit()

                resultado['success'] = True
                resultado['error'] = 'Nenhum item para processar'
                return resultado

            item_ids = [i.id for i in itens]

            # Chamar a funcao de processamento de itens diretamente
            # (reutiliza a logica, evita duplicacao)
            # Nota: get_current_job() retornara o job do lote
            result = processar_itens_baixa_job(item_ids, usuario_nome)

            # Atualizar resultado
            resultado['total_itens'] = result.get('total_itens', 0)
            resultado['itens_sucesso'] = result.get('itens_sucesso', 0)
            resultado['itens_erro'] = result.get('itens_erro', 0)
            resultado['success'] = result.get('success', False)

            # Atualizar lote
            lote.status = 'CONCLUIDO'
            lote.processado_em = agora_utc_naive()
            lote.linhas_processadas = resultado['total_itens']
            lote.linhas_sucesso = resultado['itens_sucesso']
            lote.linhas_erro = resultado['itens_erro']
            db.session.commit()

            tempo_total = (agora_utc_naive() - inicio).total_seconds()
            resultado['tempo_segundos'] = tempo_total

            logger.info(
                f"[Job Baixa Lote] Lote {lote_id} concluido em {tempo_total:.1f}s - "
                f"Sucesso: {resultado['itens_sucesso']}, Erro: {resultado['itens_erro']}"
            )

            return resultado

    except Exception as e:
        tempo_total = (agora_utc_naive() - inicio).total_seconds()
        resultado['tempo_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['success'] = False

        logger.error(f"[Job Baixa Lote] Erro geral lote {lote_id}: {e}")
        logger.error(traceback.format_exc())

        # Tentar atualizar status do lote para erro
        try:
            with _app_context_safe():
                from app import db
                from app.financeiro.models import BaixaTituloLote

                lote = db.session.get(BaixaTituloLote,lote_id) if lote_id else None
                if lote:
                    lote.status = 'ERRO'
                    lote.processado_em = agora_utc_naive()
                    db.session.commit()
        except Exception:
            pass

        return resultado


# ========================================
# FUNCOES AUXILIARES
# ========================================


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Obtem status de um job pelo ID.

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
            'meta': job.meta
        }

        # Calcular tempo de execucao se disponivel
        # RQ armazena started_at/ended_at como UTC aware
        if job.started_at and job.ended_at:
            result['duracao_segundos'] = (job.ended_at - job.started_at).total_seconds()
        elif job.started_at:
            from datetime import datetime as dt_cls, timezone
            result['duracao_segundos'] = (dt_cls.now(timezone.utc) - job.started_at).total_seconds()

        # Adicionar progresso do Redis se disponivel
        progresso = obter_progresso_baixa(job_id)
        if progresso:
            result['progresso'] = progresso

        return result

    except Exception as e:
        return {
            'job_id': job_id,
            'status': 'not_found',
            'status_display': 'Nao encontrado',
            'error': str(e)
        }
