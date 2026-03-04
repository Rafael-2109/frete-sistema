"""
Briefing Inter-Sessão MVP (Memory System v2 — Fase 3A).

Gera bloco XML compacto (~400 chars) com eventos ocorridos entre sessões:
- Erros de sync Odoo (últimas 6h)
- Falhas de importação de pedidos
- Estado de memórias (conflitos, cold candidates)

Sem nova tabela — queries diretas em tabelas existentes.
Best-effort: falhas são logadas silenciosamente.

Custo: zero (queries SQL leves, sem chamada LLM).
Trigger: início de cada sessão, via Tier 0b em client.py.
"""

import logging
from typing import Optional

from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def build_intersession_briefing(user_id: int) -> Optional[str]:
    """
    Gera briefing inter-sessão: o que mudou desde a última sessão do usuário.

    Queries leves em tabelas existentes. Retorna XML compacto ou None.

    Args:
        user_id: ID do usuário no banco

    Returns:
        XML string (~400 chars) ou None se não houver eventos relevantes.
    """
    try:
        parts = []

        # 1. Última sessão do usuário (para saber "desde quando" informar)
        last_session_at = _get_last_session_time(user_id)

        # 2. Erros de sync Odoo (últimas 6h ou desde última sessão)
        odoo_errors = _check_odoo_sync_errors(last_session_at)
        if odoo_errors:
            parts.append(odoo_errors)

        # 3. Falhas de importação de pedidos
        import_failures = _check_import_failures(last_session_at)
        if import_failures:
            parts.append(import_failures)

        # 4. Memórias com conflito pendente
        memory_alerts = _check_memory_alerts(user_id)
        if memory_alerts:
            parts.append(memory_alerts)

        if not parts:
            return None

        since = last_session_at.strftime('%d/%m %H:%M') if last_session_at else '?'
        header = f'<intersession_briefing since="{since}">'
        footer = '</intersession_briefing>'
        return header + '\n' + '\n'.join(parts) + '\n' + footer

    except Exception as e:
        logger.debug(f"[BRIEFING] Erro ao gerar briefing (ignorado): {e}")
        return None


def _get_last_session_time(user_id: int):
    """Retorna timestamp da última sessão do usuário ou None."""
    try:
        from ..models import AgentSession

        last = AgentSession.query.filter_by(
            user_id=user_id,
        ).order_by(
            AgentSession.updated_at.desc()
        ).first()

        return last.updated_at if last else None
    except Exception:
        return None


def _check_odoo_sync_errors(since) -> Optional[str]:
    """
    Verifica erros de sync Odoo desde a última sessão.

    Fonte: lancamento_frete_odoo_auditoria (status=ERRO).
    Fallback para últimas 6h se since=None.
    """
    try:
        from app import db
        from sqlalchemy import text as sql_text
        from datetime import timedelta

        now = agora_utc_naive()
        cutoff = since if since else (now - timedelta(hours=6))

        # Contar erros por etapa
        result = db.session.execute(sql_text("""
            SELECT etapa, etapa_descricao, count(*) as cnt
            FROM lancamento_frete_odoo_auditoria
            WHERE status = 'ERRO'
              AND executado_em >= :cutoff
            GROUP BY etapa, etapa_descricao
            ORDER BY cnt DESC
            LIMIT 3
        """), {"cutoff": cutoff})

        rows = result.fetchall()
        if not rows:
            return None

        total_errors = sum(r[2] for r in rows)
        top_etapa = rows[0][1] if rows else 'N/A'

        return (
            f'<odoo_sync_errors total="{total_errors}" since="{cutoff.strftime("%d/%m %H:%M")}">'
            f'Top: {top_etapa} ({rows[0][2]}x)'
            f'</odoo_sync_errors>'
        )

    except Exception as e:
        logger.debug(f"[BRIEFING] Odoo sync check falhou (ignorado): {e}")
        return None


def _check_import_failures(since) -> Optional[str]:
    """
    Verifica falhas de importação de pedidos Odoo.

    Fonte: registro_pedido_odoo (status_odoo=ERRO).
    """
    try:
        from app import db
        from sqlalchemy import text as sql_text
        from datetime import timedelta

        now = agora_utc_naive()
        cutoff = since if since else (now - timedelta(hours=6))

        result = db.session.execute(sql_text("""
            SELECT count(*)
            FROM registro_pedido_odoo
            WHERE status_odoo = 'ERRO'
              AND processado_em >= :cutoff
        """), {"cutoff": cutoff})

        count = result.scalar() or 0
        if count == 0:
            return None

        return f'<import_failures count="{count}" since="{cutoff.strftime("%d/%m %H:%M")}"/>'

    except Exception as e:
        logger.debug(f"[BRIEFING] Import check falhou (ignorado): {e}")
        return None


def _check_memory_alerts(user_id: int) -> Optional[str]:
    """
    Verifica alertas de memória: conflitos pendentes, cold candidates.

    Alertas:
    - Memórias com has_potential_conflict=True
    - Memórias candidatas a tier frio (usage_count >= 20, effectiveness_score < 0.1)
    """
    try:
        from ..models import AgentMemory

        alerts = []

        # Conflitos pendentes
        try:
            conflicts = AgentMemory.query.filter_by(
                user_id=user_id,
                has_potential_conflict=True,
                is_directory=False,
            ).count()
            if conflicts > 0:
                alerts.append(f'conflitos={conflicts}')
        except Exception:
            pass

        # Cold candidates: usage_count >= 20 e nunca efetivo
        try:
            cold_candidates = AgentMemory.query.filter(
                AgentMemory.user_id == user_id,
                AgentMemory.is_directory == False,  # noqa: E712
                AgentMemory.is_cold == False,  # noqa: E712
                AgentMemory.usage_count >= 20,
                AgentMemory.effective_count == 0,
            ).count()
            if cold_candidates > 0:
                alerts.append(f'cold_candidates={cold_candidates}')
        except Exception:
            pass

        if not alerts:
            return None

        return f'<memory_alerts {" ".join(alerts)}/>'

    except Exception as e:
        logger.debug(f"[BRIEFING] Memory alerts check falhou (ignorado): {e}")
        return None
