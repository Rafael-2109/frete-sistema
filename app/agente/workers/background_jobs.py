"""
Background jobs do agente — enfileirados em RQ para liberar worker do chat.

Antes (sincrono in-worker):
  POST_SESSION → summarize_and_save (Sonnet ~7s BLOQUEANTE) →
                analyze_patterns_and_save (Sonnet ~6s BLOQUEANTE) →
                generate_profile (Sonnet ~10s BLOQUEANTE) →
                extrair_conhecimento (Thread daemon=False ~5s) →
                extrair_insights_pessoais (Thread daemon=False ~7s)
  Total: ~35s ocupando thread do worker que processou a sessao.

Depois (RQ):
  POST_SESSION → enqueue_summarize (~10ms) +
                enqueue_patterns (~10ms) + ... → worker chat LIBRE
  Background jobs rodam isolados em sistema-fretes-worker-atacadao,
  na fila agent_background (perfil LIGHT-RESERVED).

Sintoma resolvido: Worker dono saturado por Sonnet calls em background
estava fazendo gunicorn rotear requests subsequentes para outros workers,
que retornavam 409 (sticky session). Movendo para RQ, worker dono fica
disponivel imediatamente apos Stop hook.

Ref:
- docs/agente/POST_SESSION_RQ_MIGRATION.md (criado neste PR)
- Discussao com Rafael 2026-05-27: "outros agentes consumindo worker do chat"

Rollback: AGENT_POST_SESSION_VIA_RQ=false volta para inline (Thread/sync).
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


# =====================================================================
# Jobs RQ — cada um e self-contained com app_context proprio.
# Chamados via queue.enqueue(); rodam em worker RQ separado.
# =====================================================================

def summarize_session_job(session_id: str, user_id: int) -> bool:
    """Job RQ: gera resumo da sessao via Sonnet e salva no DB."""
    try:
        from app import create_app
        from app.agente.services.session_summarizer import summarize_and_save
        app = create_app()
        return summarize_and_save(app=app, session_id=session_id, user_id=user_id)
    except Exception as e:
        logger.error(f"[RQ_JOB summarize] session={session_id[:8]}... erro: {e}", exc_info=True)
        return False


def analyze_patterns_job(user_id: int) -> bool:
    """Job RQ: analisa padroes do usuario via Sonnet + salva memoria + perfil."""
    try:
        from app import create_app
        from app.agente.services.pattern_analyzer import analyze_and_save
        app = create_app()
        return analyze_and_save(app=app, user_id=user_id)
    except Exception as e:
        logger.error(f"[RQ_JOB patterns] user={user_id} erro: {e}", exc_info=True)
        return False


def generate_profile_job(user_id: int) -> bool:
    """Job RQ: gera/atualiza user.xml (perfil comportamental) via Sonnet."""
    try:
        from app import create_app
        from app.agente.services.pattern_analyzer import generate_and_save_profile
        app = create_app()
        return generate_and_save_profile(app=app, user_id=user_id)
    except Exception as e:
        logger.error(f"[RQ_JOB profile] user={user_id} erro: {e}", exc_info=True)
        return False


def extract_knowledge_job(
    user_id: int,
    session_messages: List[Any],
    session_id: str,
    include_subagents: bool = True,
) -> bool:
    """Job RQ: extrai memoria empresa (taxonomia 5 niveis) via Sonnet."""
    try:
        from app import create_app
        from app.agente.services.pattern_analyzer import extrair_conhecimento_sessao
        app = create_app()
        extrair_conhecimento_sessao(
            app=app,
            user_id=user_id,
            session_messages=session_messages,
            include_subagents=include_subagents,
            session_id=session_id,
        )
        return True
    except Exception as e:
        logger.error(f"[RQ_JOB knowledge_extract] user={user_id} erro: {e}", exc_info=True)
        return False


def extract_personal_insights_job(user_id: int, session_messages: List[Any]) -> bool:
    """Job RQ: extrai memorias pessoais (correcao/preferencia/expertise) via Sonnet."""
    try:
        from app import create_app
        from app.agente.services.pattern_analyzer import extrair_insights_pessoais_sessao
        app = create_app()
        extrair_insights_pessoais_sessao(
            app=app,
            user_id=user_id,
            session_messages=session_messages,
        )
        return True
    except Exception as e:
        logger.error(f"[RQ_JOB personal_extract] user={user_id} erro: {e}", exc_info=True)
        return False


# =====================================================================
# Enqueue helpers — chamados pelo _helpers.py (rota POST_SESSION)
# =====================================================================

def _is_rq_enabled() -> bool:
    """Lazy check da feature flag (lida fresh do env)."""
    import os
    return os.getenv("AGENT_POST_SESSION_VIA_RQ", "false").lower() == "true"


def _get_queue():
    """Lazy import + lazy connection da fila agent_background.

    Returns None se RQ/Redis indisponivel — caller cai no fallback
    (Thread/sync) automaticamente.
    """
    try:
        from rq import Queue
        from app.utils.redis_cache import redis_cache
        if not redis_cache.disponivel:
            return None
        return Queue("agent_background", connection=redis_cache.client)
    except Exception as e:
        logger.debug(f"[RQ] Queue indisponivel: {e}")
        return None


def try_enqueue_summarize(session_id: str, user_id: int) -> bool:
    """Enfileira summarize. Retorna True se enfileirou, False = caller faz fallback."""
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            summarize_session_job,
            session_id, user_id,
            job_timeout=120,  # 2min — Sonnet call + DB writes
            description=f"summarize {session_id[:8]}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue summarize falhou (fallback inline): {e}")
        return False


def try_enqueue_analyze_patterns(user_id: int) -> bool:
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            analyze_patterns_job,
            user_id,
            job_timeout=180,  # 3min — Sonnet + piggyback user.xml
            description=f"patterns user={user_id}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue patterns falhou (fallback inline): {e}")
        return False


def try_enqueue_generate_profile(user_id: int) -> bool:
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            generate_profile_job,
            user_id,
            job_timeout=180,
            description=f"profile user={user_id}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue profile falhou (fallback inline): {e}")
        return False


def try_enqueue_extract_knowledge(
    user_id: int,
    session_messages: List[Any],
    session_id: str,
    include_subagents: bool = True,
) -> bool:
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            extract_knowledge_job,
            user_id, session_messages, session_id, include_subagents,
            job_timeout=180,
            description=f"knowledge user={user_id} session={session_id[:8]}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue knowledge falhou (fallback inline): {e}")
        return False


def try_enqueue_extract_personal_insights(
    user_id: int,
    session_messages: List[Any],
) -> bool:
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            extract_personal_insights_job,
            user_id, session_messages,
            job_timeout=180,
            description=f"personal user={user_id}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue personal falhou (fallback inline): {e}")
        return False


def skill_effectiveness_job(session_id: str, user_id: int) -> bool:
    """Job RQ: avalia efetividade das skills invocadas na sessao."""
    try:
        from app import create_app
        from app.agente.services.skill_effectiveness_service import evaluate_session
        app = create_app()
        evaluate_session(session_id=session_id, user_id=user_id, app=app)
        return True
    except Exception as e:
        logger.error(f"[RQ_JOB skill_eval] session={session_id[:8]}... erro: {e}", exc_info=True)
        return False


def try_enqueue_skill_effectiveness(session_id: str, user_id: int) -> bool:
    """Enfileira avaliacao de efetividade de skill. Retorna True se enfileirou, False = caller faz fallback."""
    if not _is_rq_enabled():
        return False
    q = _get_queue()
    if q is None:
        return False
    try:
        q.enqueue(
            skill_effectiveness_job,
            session_id, user_id,
            job_timeout=180,
            description=f"skill_eval {session_id[:8]}",
        )
        return True
    except Exception as e:
        logger.warning(f"[RQ] enqueue skill_eval falhou (fallback inline): {e}")
        return False
