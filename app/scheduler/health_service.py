"""
Service: Scheduler Health
=========================

Grava resultado de cada step e fornece dados para dashboard.
"""

import logging
from app import db
from app.scheduler.models import SchedulerHealth
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def registrar_step(step_name: str, step_number: int, sucesso: bool,
                   duracao_ms: int = None, erro: str = None, detalhes: str = None):
    """Registra resultado de um step do scheduler."""
    try:
        registro = SchedulerHealth(
            step_name=step_name,
            step_number=step_number,
            executado_em=agora_utc_naive(),
            status='OK' if sucesso else 'ERRO',
            duracao_ms=duracao_ms,
            erro=erro[:2000] if erro else None,
            detalhes=detalhes[:500] if detalhes else None,
        )
        db.session.add(registro)
        db.session.commit()
    except Exception as e:
        logger.warning(f"Falha ao registrar scheduler health ({step_name}): {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def obter_status_steps():
    """Retorna ultimo status de cada step (para dashboard)."""
    try:
        from sqlalchemy import func

        # Subquery: ultima execucao por step
        subq = db.session.query(
            SchedulerHealth.step_name,
            func.max(SchedulerHealth.id).label('max_id')
        ).group_by(SchedulerHealth.step_name).subquery()

        resultados = db.session.query(SchedulerHealth).join(
            subq, SchedulerHealth.id == subq.c.max_id
        ).order_by(SchedulerHealth.step_number).all()

        return [{
            'step_name': r.step_name,
            'step_number': r.step_number,
            'status': r.status,
            'executado_em': r.executado_em.strftime('%d/%m/%Y %H:%M') if r.executado_em else None,
            'duracao_ms': r.duracao_ms,
            'erro': r.erro,
            'detalhes': r.detalhes,
        } for r in resultados]
    except Exception as e:
        logger.error(f"Erro ao obter status scheduler: {e}")
        return []


def limpar_registros_antigos(dias: int = 7):
    """Remove registros mais antigos que N dias (manter tabela leve)."""
    try:
        from datetime import timedelta
        limite = agora_utc_naive() - timedelta(days=dias)
        deleted = SchedulerHealth.query.filter(
            SchedulerHealth.executado_em < limite
        ).delete()
        db.session.commit()
        logger.info(f"Scheduler health: {deleted} registros antigos removidos")
        return deleted
    except Exception as e:
        logger.error(f"Erro ao limpar registros scheduler health: {e}")
        db.session.rollback()
        return 0
