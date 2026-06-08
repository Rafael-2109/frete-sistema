"""Inbox de Aprovacao unificada: AgentMemory shadow + ImprovementDialogue proposed.

Conserta o gap do directive_promotion (shadow->ativa nunca teve UI). Best-effort nas
leituras; writes commitam com try/except + rollback.

Ver spec: docs/superpowers/specs/2026-06-07-aprendizado-efetividade-skills-design.md
"""
import logging

logger = logging.getLogger(__name__)


def list_pending_approvals() -> list:
    """Lista itens pendentes de decisao humana (memory shadow + dialogue proposed).

    Semantica:
    - memory shadow: pode Aprovar (->ativa) ou Rejeitar (->despromovida).
    - dialogue proposed: so Rejeitar (Claude Code implementa os que seguem 'proposed').
    """
    out = []
    try:
        from app.agente.models import AgentMemory, AgentImprovementDialogue
        for m in AgentMemory.query.filter(
                AgentMemory.directive_status == 'shadow').order_by(
                AgentMemory.created_at.desc()).limit(200).all():
            out.append({
                "kind": "memory",
                "id": m.id,
                "title": m.path.rsplit('/', 1)[-1],
                "scope": "empresa" if m.user_id == 0 else f"user:{m.user_id}",
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "can_approve": True,
            })
        for d in AgentImprovementDialogue.query.filter_by(
                status='proposed').order_by(
                AgentImprovementDialogue.created_at.desc()).limit(200).all():
            out.append({
                "kind": "dialogue",
                "id": d.id,
                "title": d.title,
                "category": d.category,
                "content": d.description,
                "evidence": d.evidence_json or {},
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "can_approve": False,  # Claude Code implementa os que seguem 'proposed'
            })
    except Exception as e:
        logger.warning(f"[INBOX] list falhou: {e}")
    return out


def approve_item(kind: str, item_id: int, reviewer_user_id: int) -> bool:
    """Aprova. memory shadow -> 'ativa' (passa a injetar). dialogue: nao aplicavel.

    Returns True se aprovacao foi aplicada, False caso contrario.
    """
    from app import db
    if kind != "memory":
        logger.info(f"[INBOX] approve nao aplicavel para kind={kind}")
        return False
    try:
        from app.agente.models import AgentMemory
        m = AgentMemory.query.get(item_id)
        if not m or m.directive_status != 'shadow':
            return False
        m.directive_status = 'ativa'
        m.reviewed_at = _now()
        db.session.commit()
        # Invalidar caches de injecao (best-effort)
        try:
            from app.agente.sdk.memory_injection import (
                invalidate_injection_cache_for_user, invalidate_skill_reminders_cache)
            invalidate_injection_cache_for_user(m.user_id)
            invalidate_skill_reminders_cache()
        except Exception as e_cache:
            logger.debug(f"[INBOX] invalidate cache falhou: {e_cache}")
        logger.info(
            f"[INBOX] memory {item_id} APROVADA->ativa por user={reviewer_user_id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.warning(f"[INBOX] approve falhou: {e}")
        return False


def reject_item(kind: str, item_id: int, reviewer_user_id: int) -> bool:
    """Rejeita. memory -> 'despromovida'; dialogue -> status 'rejected'.

    Returns True se rejeicao foi aplicada, False caso contrario.
    """
    from app import db
    try:
        if kind == "memory":
            from app.agente.models import AgentMemory
            m = AgentMemory.query.get(item_id)
            if not m:
                return False
            m.directive_status = 'despromovida'
            m.reviewed_at = _now()
            db.session.commit()
            # Invalidar caches de injecao (best-effort)
            try:
                from app.agente.sdk.memory_injection import invalidate_skill_reminders_cache
                invalidate_skill_reminders_cache()
            except Exception as e_cache:
                logger.debug(f"[INBOX] invalidate cache falhou: {e_cache}")
            logger.info(
                f"[INBOX] memory {item_id} REJEITADA->despromovida por user={reviewer_user_id}")
            return True
        elif kind == "dialogue":
            from app.agente.models import AgentImprovementDialogue
            d = AgentImprovementDialogue.query.get(item_id)
            if not d:
                return False
            d.status = 'rejected'
            db.session.commit()
            logger.info(
                f"[INBOX] dialogue {item_id} REJEITADO por user={reviewer_user_id}")
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.warning(f"[INBOX] reject falhou: {e}")
        return False


def _now():
    """Retorna timestamp UTC naive (padrao do projeto)."""
    from app.utils.timezone import agora_utc_naive
    return agora_utc_naive()
