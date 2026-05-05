"""RQ worker para backfill enriquecedor de pedidos TagPlus.

Mecanismo:
  1. `enfileirar_backfill_pedidos_job(...)` cria HoraTagPlusBackfillJob
     com tipo='PEDIDO_ENRIQUECIMENTO' e enfileira esta funcao.
  2. Este worker pega o job, marca EM_PROGRESSO, executa
     `executar_backfill_pedidos(progress_callback=...)`.
  3. O callback eh invocado a cada emissao processada — gravamos
     progresso em sessao SQLAlchemy SEPARADA para nao misturar com
     transacao do enriquecimento (que faz commit por venda).
"""
from __future__ import annotations

import logging

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


def _gravar_progresso(job_id: int, snap: dict) -> None:
    """Atualiza job com snapshot incremental do executar_backfill_pedidos.

    Usa contadores existentes do HoraTagPlusBackfillJob:
      - n_atualizado     <- snap['enriquecidas']
      - n_inalterado     <- snap['inalteradas']
      - n_pulada_invalida <- snap['sem_pedido'] + snap['sem_venda']
      - n_erro           <- snap['erro_pedido']
      - relatorio.erros  <- snap['erros']
    """
    from app import db
    from app.hora.models import HoraTagPlusBackfillJob
    from app.utils.json_helpers import sanitize_for_json
    from app.utils.timezone import agora_utc_naive

    try:
        job = db.session.get(HoraTagPlusBackfillJob, job_id)
        if job is None:
            return
        job.processadas = snap.get('processadas', 0)
        job.n_atualizado = snap.get('enriquecidas', 0)
        job.n_inalterado = snap.get('inalteradas', 0)
        job.n_pulada_invalida = (
            snap.get('sem_pedido', 0) + snap.get('sem_venda', 0)
        )
        job.n_erro = snap.get('erro_pedido', 0)
        job.atualizado_em = agora_utc_naive()
        erros_snap = snap.get('erros') or []
        if erros_snap:
            relatorio_atual = dict(job.relatorio or {})
            relatorio_atual['erros'] = sanitize_for_json(erros_snap)
            job.relatorio = relatorio_atual
        db.session.commit()
    except Exception:
        logger.exception('Falha ao gravar progresso pedido-backfill job %s', job_id)
        try:
            db.session.rollback()
        except Exception:
            pass


def _marcar_inicio(job_id: int) -> None:
    from app import db
    from app.hora.models import (
        BACKFILL_JOB_STATUS_EM_PROGRESSO,
        HoraTagPlusBackfillJob,
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
        job.relatorio = sanitize_for_json(relatorio)
    db.session.commit()


def _contar_total_listadas() -> int:
    """Conta HoraTagPlusNfeEmissao APROVADA com tagplus_nfe_id (universo)."""
    from app import db
    from app.hora.models import HoraTagPlusNfeEmissao, NFE_STATUS_APROVADA

    return db.session.query(HoraTagPlusNfeEmissao).filter(
        HoraTagPlusNfeEmissao.status == NFE_STATUS_APROVADA,
        HoraTagPlusNfeEmissao.tagplus_nfe_id.isnot(None),
    ).count()


def processar_backfill_pedidos_job(job_id: int) -> None:
    """Job RQ: enriquece HoraVenda via GET /pedidos/{id} TagPlus.

    Funcao `enqueue`-ada por `enfileirar_backfill_pedidos_job`. Retorna None
    — resultado fica em HoraTagPlusBackfillJob.relatorio.
    """
    ctx = _ensure_app_context()
    try:
        from app import db
        from app.hora.models import (
            BACKFILL_JOB_STATUS_CONCLUIDO,
            BACKFILL_JOB_STATUS_ERRO,
            HoraTagPlusBackfillJob,
        )
        from app.hora.services.tagplus.pedido_backfill_service import (
            executar_backfill_pedidos,
        )

        job = db.session.get(HoraTagPlusBackfillJob, job_id)
        if job is None:
            logger.error('processar_backfill_pedidos_job: job %s nao existe', job_id)
            return

        limite = job.limite
        operador = job.operador

        logger.info(
            'Iniciando backfill PEDIDOS job_id=%s limite=%s operador=%s',
            job_id, limite, operador,
        )

        _marcar_inicio(job_id)

        # Pre-contagem (best-effort).
        try:
            total = _contar_total_listadas()
            if total:
                job = db.session.get(HoraTagPlusBackfillJob, job_id)
                if job is not None:
                    job.total_listadas = (
                        min(limite, total) if limite else total
                    )
                    db.session.commit()
        except Exception:
            logger.exception('Pre-contagem total_listadas falhou — UI sem %')

        def _cb(snap: dict) -> None:
            _gravar_progresso(job_id, snap)

        try:
            relatorio = executar_backfill_pedidos(
                operador=operador, limite=limite,
                progress_callback=_cb,
            )
            _marcar_fim(job_id, BACKFILL_JOB_STATUS_CONCLUIDO, relatorio)
            logger.info(
                'Backfill PEDIDOS job_id=%s CONCLUIDO: %s', job_id,
                {k: v for k, v in relatorio.items() if k != 'erros'},
            )
        except Exception as exc:
            logger.exception('Backfill PEDIDOS job_id=%s ERRO terminal', job_id)
            try:
                db.session.rollback()
            except Exception:
                pass
            _marcar_fim(
                job_id, BACKFILL_JOB_STATUS_ERRO,
                relatorio=None, erro=f'{type(exc).__name__}: {exc}',
            )
            raise
    finally:
        if ctx is not None:
            ctx.pop()
