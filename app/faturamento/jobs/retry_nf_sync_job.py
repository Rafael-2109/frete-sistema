"""
Retry Job para Sincronizacao de NF com Faturamento
===================================================

Quando o processamento de NF falha (timeout, rede, erro de DB),
este job reenfileira a NF para retry com backoff exponencial.

Fluxo:
1. processar_faturamento.py detecta falha em NF especifica
2. Enfileira retry_nf_sync_job na fila 'faturamento'
3. Job executa ProcessadorFaturamento para a NF especifica
4. Se falha novamente: reenfileira com attempt+1 (backoff exponencial)
5. Se max_attempts excedido: loga CRITICAL e registra para intervencao manual

Backoff: delay = 60 * (2 ** attempt) segundos
  attempt 1: 120s  (2 min)
  attempt 2: 240s  (4 min)
  attempt 3: 480s  (8 min)
"""

import logging
from typing import Optional, List

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Constantes
MAX_ATTEMPTS_DEFAULT = 3
BASE_DELAY_SECONDS = 60
QUEUE_NAME = 'faturamento'
JOB_TIMEOUT = '15m'


def retry_nf_sync(
    nf_ids: List[str],
    attempt: int = 1,
    max_attempts: int = MAX_ATTEMPTS_DEFAULT,
    erro_original: Optional[str] = None,
) -> dict:
    """
    Retenta o processamento de NFs que falharam na sincronizacao.

    Executa dentro de app_context (RQ worker fornece via create_app).

    Args:
        nf_ids: Lista de numeros de NF para reprocessar
        attempt: Numero da tentativa atual (1-based)
        max_attempts: Maximo de tentativas antes de escalar
        erro_original: Mensagem do erro que causou o retry

    Returns:
        Dict com resultado do processamento
    """
    from app import create_app, db

    app = create_app()
    with app.app_context():
        resultado = {
            'success': False,
            'nf_ids': nf_ids,
            'attempt': attempt,
            'max_attempts': max_attempts,
            'erro_original': erro_original,
            'timestamp': agora_utc_naive().isoformat(),
            'processadas': 0,
            'erros': [],
        }

        logger.info(
            f"[RETRY NF SYNC] Tentativa {attempt}/{max_attempts} "
            f"para {len(nf_ids)} NFs: {nf_ids[:5]}{'...' if len(nf_ids) > 5 else ''}"
        )
        if erro_original:
            logger.info(f"[RETRY NF SYNC] Erro original: {erro_original}")

        try:
            from app.faturamento.services.processar_faturamento import ProcessadorFaturamento

            processador = ProcessadorFaturamento()
            resultado_proc = processador.processar_nfs_importadas(
                usuario='Retry NF Sync',
                nfs_especificas=nf_ids,
            )

            if resultado_proc:
                resultado['processadas'] = resultado_proc.get('processadas', 0)
                resultado['movimentacoes_criadas'] = resultado_proc.get('movimentacoes_criadas', 0)
                erros_proc = resultado_proc.get('erros', [])
                resultado['erros'] = erros_proc

                if erros_proc:
                    logger.warning(
                        f"[RETRY NF SYNC] Tentativa {attempt}: "
                        f"{resultado['processadas']} processadas, "
                        f"{len(erros_proc)} erros persistem"
                    )
                    # NFs que ainda falharam precisam de novo retry
                    _handle_persistent_failures(
                        nf_ids=nf_ids,
                        erros=erros_proc,
                        attempt=attempt,
                        max_attempts=max_attempts,
                    )
                else:
                    resultado['success'] = True
                    logger.info(
                        f"[RETRY NF SYNC] Tentativa {attempt}: SUCESSO! "
                        f"{resultado['processadas']} NFs processadas"
                    )
            else:
                msg = 'ProcessadorFaturamento retornou None'
                resultado['erros'].append(msg)
                logger.warning(f"[RETRY NF SYNC] {msg}")
                _handle_persistent_failures(
                    nf_ids=nf_ids,
                    erros=[msg],
                    attempt=attempt,
                    max_attempts=max_attempts,
                )

        except Exception as e:
            erro_msg = f"Erro na tentativa {attempt}: {str(e)}"
            resultado['erros'].append(erro_msg)
            logger.error(f"[RETRY NF SYNC] {erro_msg}", exc_info=True)

            _handle_persistent_failures(
                nf_ids=nf_ids,
                erros=[erro_msg],
                attempt=attempt,
                max_attempts=max_attempts,
            )

        return resultado


def _handle_persistent_failures(
    nf_ids: List[str],
    erros: List[str],
    attempt: int,
    max_attempts: int,
) -> None:
    """
    Trata falhas persistentes: reenfileira com backoff ou escala para intervencao manual.

    Args:
        nf_ids: NFs que falharam
        erros: Lista de erros
        attempt: Tentativa atual
        max_attempts: Maximo de tentativas
    """
    if attempt >= max_attempts:
        # Max attempts excedido - escalar para intervencao manual
        logger.critical(
            f"[RETRY NF SYNC] MAX ATTEMPTS EXCEDIDO ({max_attempts}) para NFs: {nf_ids}. "
            f"Ultimo erro: {erros[-1] if erros else 'desconhecido'}. "
            f"INTERVENCAO MANUAL NECESSARIA."
        )
        _registrar_falha_permanente(nf_ids, erros, attempt)
        return

    # Calcular delay com backoff exponencial
    next_attempt = attempt + 1
    delay_seconds = BASE_DELAY_SECONDS * (2 ** attempt)

    logger.info(
        f"[RETRY NF SYNC] Reenfileirando NFs para tentativa {next_attempt}/{max_attempts} "
        f"com delay de {delay_seconds}s ({delay_seconds // 60}min)"
    )

    try:
        from app.portal.workers import enqueue_job
        from rq import Retry

        enqueue_job(
            retry_nf_sync,
            nf_ids,
            next_attempt,
            max_attempts,
            erros[-1] if erros else None,
            queue_name=QUEUE_NAME,
            timeout=JOB_TIMEOUT,
        )

        next_retry_time = agora_utc_naive().strftime('%H:%M:%S')
        logger.info(
            f"[RETRY NF SYNC] Job reenfileirado. "
            f"Tentativa {next_attempt} agendada. "
            f"Enfileirado em: {next_retry_time}"
        )

    except Exception as e:
        logger.error(
            f"[RETRY NF SYNC] FALHA ao reenfileirar retry: {e}. "
            f"NFs {nf_ids} precisam de intervencao manual.",
            exc_info=True,
        )
        _registrar_falha_permanente(nf_ids, erros + [f"Falha ao reenfileirar: {str(e)}"], attempt)


def _registrar_falha_permanente(
    nf_ids: List[str],
    erros: List[str],
    tentativas_realizadas: int,
) -> None:
    """
    Registra falha permanente para intervencao manual.
    Loga como CRITICAL e persiste no audit log.
    """
    import json
    import os

    log_entry = {
        'tipo': 'RETRY_NF_SYNC_FALHA_PERMANENTE',
        'nf_ids': nf_ids,
        'tentativas_realizadas': tentativas_realizadas,
        'erros': erros[-3:],  # Ultimos 3 erros
        'timestamp': agora_utc_naive().isoformat(),
        'requer_intervencao_manual': True,
    }

    logger.critical(
        f"[RETRY NF SYNC] FALHA PERMANENTE registrada: {json.dumps(log_entry, ensure_ascii=False)}"
    )

    # Persistir no audit log de faturamento
    try:
        audit_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs', 'audit')
        os.makedirs(audit_dir, exist_ok=True)
        audit_file = os.path.join(audit_dir, 'faturamento_retry_falhas.jsonl')

        with open(audit_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        logger.info(f"[RETRY NF SYNC] Falha registrada em {audit_file}")
    except Exception as e:
        logger.error(f"[RETRY NF SYNC] Nao foi possivel registrar falha no audit log: {e}")


def enqueue_nf_retry(
    nf_ids: List[str],
    erro_original: Optional[str] = None,
    max_attempts: int = MAX_ATTEMPTS_DEFAULT,
) -> Optional[str]:
    """
    Funcao auxiliar para enfileirar retry de NFs.
    Chamada pelos callers (processar_faturamento, faturamento_service, etc).

    Args:
        nf_ids: Lista de NFs que falharam
        erro_original: Mensagem do erro que causou o retry
        max_attempts: Maximo de tentativas

    Returns:
        Job ID se enfileirado com sucesso, None se falhou
    """
    if not nf_ids:
        return None

    try:
        from app.portal.workers import enqueue_job

        job = enqueue_job(
            retry_nf_sync,
            nf_ids,
            1,  # attempt = 1 (primeira tentativa de retry)
            max_attempts,
            erro_original,
            queue_name=QUEUE_NAME,
            timeout=JOB_TIMEOUT,
        )

        logger.info(
            f"[RETRY NF SYNC] Job {job.id} enfileirado para {len(nf_ids)} NFs "
            f"(max_attempts={max_attempts}). "
            f"NFs: {nf_ids[:5]}{'...' if len(nf_ids) > 5 else ''}"
        )
        return job.id

    except Exception as e:
        logger.error(
            f"[RETRY NF SYNC] Falha ao enfileirar retry para NFs {nf_ids}: {e}",
            exc_info=True,
        )
        return None
