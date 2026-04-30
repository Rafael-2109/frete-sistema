"""RQ worker para backfill TagPlus em background (queue `hora_backfill`).

Mecanismo:
  1. `enfileirar_backfill_job(...)` cria HoraTagPlusBackfillJob e enfileira
     `processar_backfill_job(job_id)` em RQ.
  2. Este worker pega o job, marca EM_PROGRESSO, executa
     `executar_backfill(progress_callback=...)`.
  3. O callback eh invocado a cada NF processada — gravamos o progresso em
     uma sessao SQLAlchemy SEPARADA para nao misturar com a transacao do
     `importar_nfe_da_api` (que faz commit por NF).
  4. Resiliencia DB: o `_importar_com_retry_db` faz dispose+retry em
     OperationalError. Se mesmo apos 3 tentativas falhar, sobe para o
     try/except aqui que marca o job como ERRO + grava `ultimo_erro`.

Throttling do progresso:
  Atualizamos o job a cada 1 NF (overhead minimo: UPDATE em PK indexada).
  Em volumes maiores que 1000 NFs, considerar batchar a cada 5.
"""
from __future__ import annotations

import logging
from datetime import date as _date

logger = logging.getLogger(__name__)


def _ensure_app_context():
    """Garante app_context. RQ pode invocar fora do contexto Flask."""
    from flask import current_app
    try:
        current_app._get_current_object()  # noqa: SLF001
        return None
    except RuntimeError:
        from app import create_app
        app = create_app()
        ctx = app.app_context()
        ctx.push()
        return ctx


def _gravar_progresso(job_id: int, snapshot: dict) -> None:
    """Atualiza HoraTagPlusBackfillJob com snapshot do executar_backfill.

    IMPORTANTE: usa sessao SQLAlchemy isolada (scoped session push/pop) para
    nao interferir com a transacao do `importar_nfe_da_api`. Se a sessao
    principal estiver em estado quebrado (rollback recente), nao queremos
    propagar isso ao UPDATE de progresso.
    """
    from app import db
    from app.hora.models import HoraTagPlusBackfillJob
    from app.utils.timezone import agora_utc_naive

    try:
        job = db.session.get(HoraTagPlusBackfillJob, job_id)
        if job is None:
            logger.warning('progresso: job %s nao existe', job_id)
            return
        job.processadas = snapshot['processadas']
        job.n_criado = snapshot['criado']
        job.n_atualizado = snapshot['atualizado']
        job.n_inalterado = snapshot['inalterado']
        job.n_cancelado = snapshot['cancelado']
        job.n_pulada_cancelada = snapshot['pulada_cancelada']
        job.n_pulada_invalida = snapshot['pulada_invalida']
        job.n_dup = snapshot['duplicado']
        job.n_erro = snapshot['erro']
        job.n_divergencias = snapshot['divergencias']
        job.atualizado_em = agora_utc_naive()
        if snapshot.get('ultimo_erro'):
            job.ultimo_erro = (snapshot['ultimo_erro'] or '')[:2000]
        db.session.commit()
    except Exception:
        logger.exception('Falha ao gravar progresso do job %s', job_id)
        try:
            db.session.rollback()
        except Exception:
            pass


def _marcar_inicio(job_id: int) -> None:
    """Transiciona job para EM_PROGRESSO + iniciado_em."""
    from app import db
    from app.hora.models import (
        HoraTagPlusBackfillJob,
        BACKFILL_JOB_STATUS_EM_PROGRESSO,
    )
    from app.utils.timezone import agora_utc_naive

    job = db.session.get(HoraTagPlusBackfillJob, job_id)
    if job is None:
        raise RuntimeError(f'job {job_id} nao existe')
    job.status = BACKFILL_JOB_STATUS_EM_PROGRESSO
    job.iniciado_em = agora_utc_naive()
    db.session.commit()


def _marcar_fim(job_id: int, status: str, relatorio: dict | None,
                erro: str | None = None) -> None:
    """Transiciona job para CONCLUIDO ou ERRO + finalizado_em + relatorio."""
    from app import db
    from app.hora.models import HoraTagPlusBackfillJob
    from app.utils.json_helpers import sanitize_for_json
    from app.utils.timezone import agora_utc_naive

    job = db.session.get(HoraTagPlusBackfillJob, job_id)
    if job is None:
        return
    job.status = status
    job.finalizado_em = agora_utc_naive()
    if erro:
        job.ultimo_erro = erro[:2000]
    if relatorio is not None:
        # Remove a lista detalhada `resultados` antes de persistir — pode
        # ficar grande (1 entrada por NF). Mantem so contadores.
        rel_compacto = {k: v for k, v in relatorio.items() if k != 'resultados'}
        job.relatorio = sanitize_for_json(rel_compacto)
    db.session.commit()


def _contar_total_listadas(since: _date | None, until: _date | None) -> int:
    """Pre-conta NFes no intervalo via API TagPlus para popular total_listadas.

    Iteracao paginada — sem cap (worker roda em background com job_timeout=2h).
    Retorna 0 se a contagem falhar (UI mostra '?' em vez de progresso %).
    """
    from app.hora.models.tagplus import HoraTagPlusConta
    from app.hora.services.tagplus.api_client import ApiClient
    from app.hora.services.tagplus.backfill_service import listar_nfes_emitidas

    try:
        conta = HoraTagPlusConta.ativa()
        if conta is None:
            return 0
        api = ApiClient(conta)
        total = 0
        for _ in listar_nfes_emitidas(api, since=since, until=until):
            total += 1
        return total
    except Exception:
        logger.exception('Pre-contagem total_listadas falhou — UI sem %')
        return 0


def processar_backfill_job(job_id: int) -> None:
    """Job RQ: executa backfill com progresso incremental e resiliencia DB.

    Funcao `enqueue`-ada por `enfileirar_backfill_job`. Retorna None — o
    resultado fica em `HoraTagPlusBackfillJob.relatorio`.
    """
    ctx = _ensure_app_context()
    try:
        from app import db
        from app.hora.models import (
            HoraTagPlusBackfillJob,
            BACKFILL_JOB_STATUS_CONCLUIDO,
            BACKFILL_JOB_STATUS_ERRO,
        )
        from app.hora.services.tagplus.backfill_service import executar_backfill

        # Carrega parametros do job.
        job = db.session.get(HoraTagPlusBackfillJob, job_id)
        if job is None:
            logger.error('processar_backfill_job: job %s nao existe', job_id)
            return

        since = job.since
        until = job.until
        limite = job.limite
        operador = job.operador

        logger.info(
            'Iniciando backfill job_id=%s since=%s until=%s limite=%s operador=%s',
            job_id, since, until, limite, operador,
        )

        _marcar_inicio(job_id)

        # Pre-contagem (best-effort) para alimentar progresso %.
        total_listadas = _contar_total_listadas(since, until)
        if total_listadas:
            job = db.session.get(HoraTagPlusBackfillJob, job_id)
            if job is not None:
                job.total_listadas = (
                    min(limite, total_listadas) if limite else total_listadas
                )
                db.session.commit()

        def _cb(snap: dict) -> None:
            _gravar_progresso(job_id, snap)

        try:
            relatorio = executar_backfill(
                since=since, until=until, operador=operador, limite=limite,
                progress_callback=_cb,
            )
            _marcar_fim(job_id, BACKFILL_JOB_STATUS_CONCLUIDO, relatorio)
            logger.info(
                'Backfill job_id=%s CONCLUIDO: %s', job_id, {
                    k: v for k, v in relatorio.items()
                    if k != 'resultados'
                },
            )
        except Exception as exc:
            logger.exception('Backfill job_id=%s ERRO terminal', job_id)
            try:
                db.session.rollback()
            except Exception:
                pass
            _marcar_fim(
                job_id, BACKFILL_JOB_STATUS_ERRO,
                relatorio=None, erro=f'{type(exc).__name__}: {exc}',
            )
            # Re-raise para RQ saber que o job falhou e aplicar retry.
            raise
    finally:
        if ctx is not None:
            ctx.pop()
