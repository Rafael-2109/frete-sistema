"""
teams_observability_service — KPIs de observabilidade do canal Teams.

Duas fontes:
  - OPERACIONAL: `teams_tasks` (volume, status, latencia, fila, usuarios, travadas)
  - CUSTO/QUALIDADE: `agent_step` (channel='teams') + `agent_skill_effectiveness`
    (sessoes Teams via session_id LIKE 'teams_%').

Read-only. Funciona com tabelas vazias (retorna zeros/listas vazias).
Espelha o padrao de `metrics_dashboard_service.py` (period -> cutoff naive-UTC).

O channel do Teams e gravado em:
  - `AgentStep.channel = 'teams'` (coluna SQL — fonte robusta) — teams/services.py:282
  - `AgentSession.data['channel'] = 'teams'` (JSONB) — teams/services.py:699
  - session_id das sessoes Teams = f"teams_{conversation_id}" — teams/services.py:652
"""
import logging
from collections import Counter
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Estados em que uma task ainda "deve" progredir (candidatos a travamento)
WAITING_STATES = ('pending', 'processing', 'awaiting_user_input', 'queued')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_period_hours(period: str) -> int:
    """Converte '24h'|'7d'|'30d' em horas. Default seguro = 7d."""
    return {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}.get(period, 24 * 7)


def _cutoff(period: str):
    """Timestamp naive-UTC de corte para o periodo."""
    return agora_utc_naive() - timedelta(hours=_resolve_period_hours(period))


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Percentil por interpolacao linear. `sorted_values` ja ordenado asc."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


# ---------------------------------------------------------------------------
# OPERACIONAL — teams_tasks
# ---------------------------------------------------------------------------

def count_by_status(period: str = "7d") -> Dict[str, int]:
    """Contagem de tasks por status criadas no periodo."""
    from app.teams.models import TeamsTask
    cutoff = _cutoff(period)
    rows = (
        db.session.query(TeamsTask.status, func.count(TeamsTask.id))
        .filter(TeamsTask.created_at >= cutoff)
        .group_by(TeamsTask.status)
        .all()
    )
    return {status: int(cnt) for status, cnt in rows}


def get_overview(period: str = "7d") -> Dict[str, Any]:
    """KPIs operacionais do Teams no periodo."""
    from app.teams.models import TeamsTask
    cutoff = _cutoff(period)
    by_status = count_by_status(period)
    total = sum(by_status.values())

    def pct(status: str) -> float:
        return round(100.0 * by_status.get(status, 0) / total, 1) if total else 0.0

    # Latencia end-to-end (bruta — inclui tempo de espera em awaiting_user_input)
    lat_rows = (
        db.session.query(TeamsTask.created_at, TeamsTask.completed_at)
        .filter(TeamsTask.created_at >= cutoff, TeamsTask.completed_at.isnot(None))
        .all()
    )
    lats = sorted(
        (c2 - c1).total_seconds()
        for c1, c2 in lat_rows
        if c1 and c2 and (c2 - c1).total_seconds() >= 0
    )
    latencia_media_s = round(sum(lats) / len(lats), 1) if lats else None
    latencia_p95_s = round(_percentile(lats, 95), 1) if lats else None

    usuarios_ativos = (
        db.session.query(func.count(func.distinct(TeamsTask.user_id)))
        .filter(TeamsTask.created_at >= cutoff, TeamsTask.user_id.isnot(None))
        .scalar()
    ) or 0

    # Fila atual = snapshot AGORA (independe do periodo)
    fila_atual = (
        db.session.query(func.count(TeamsTask.id))
        .filter(TeamsTask.status == "queued")
        .scalar()
    ) or 0

    travadas = len(get_stuck_tasks())

    return {
        "period": period,
        "total": total,
        "by_status": by_status,
        "taxa_sucesso": pct("completed"),
        "taxa_erro": pct("error"),
        "taxa_timeout": pct("timeout"),
        "latencia_media_s": latencia_media_s,
        "latencia_p95_s": latencia_p95_s,
        "usuarios_ativos": int(usuarios_ativos),
        "fila_atual": int(fila_atual),
        "travadas": travadas,
    }


def get_stuck_tasks(threshold_min: int = 10, limit: int = 50) -> List[Dict[str, Any]]:
    """Snapshot (independe de periodo) de tasks em estado de espera ha > threshold_min."""
    from app.teams.models import TeamsTask
    now = agora_utc_naive()
    cutoff = now - timedelta(minutes=threshold_min)
    rows = (
        TeamsTask.query
        .filter(TeamsTask.status.in_(WAITING_STATES), TeamsTask.updated_at < cutoff)
        .order_by(TeamsTask.updated_at.asc())
        .limit(limit)
        .all()
    )
    out = []
    for t in rows:
        age_min = round((now - t.updated_at).total_seconds() / 60.0, 1) if t.updated_at else None
        out.append({
            "id": t.id,
            "conversation_id": t.conversation_id,
            "status": t.status,
            "user_id": t.user_id,
            "user_name": t.user_name,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "age_min": age_min,
            "mensagem_preview": (t.mensagem or "")[:80],
        })
    return out


def get_top_users(period: str = "7d", limit: int = 10) -> List[Dict[str, Any]]:
    """Usuarios mais ativos no Teams no periodo (por volume de tasks)."""
    from app.teams.models import TeamsTask
    cutoff = _cutoff(period)
    rows = (
        db.session.query(
            TeamsTask.user_id,
            func.max(TeamsTask.user_name),
            func.count(TeamsTask.id),
        )
        .filter(TeamsTask.created_at >= cutoff, TeamsTask.user_id.isnot(None))
        .group_by(TeamsTask.user_id)
        .order_by(func.count(TeamsTask.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {"user_id": uid, "user_name": uname, "count": int(cnt)}
        for uid, uname, cnt in rows
    ]


def get_timeseries(period: str = "7d") -> List[Dict[str, Any]]:
    """Serie temporal de volume por bucket (hora se '24h', dia caso contrario)."""
    from app.teams.models import TeamsTask
    cutoff = _cutoff(period)
    trunc = "hour" if period == "24h" else "day"
    bucket = func.date_trunc(trunc, TeamsTask.created_at)
    rows = (
        db.session.query(
            bucket.label("bucket"),
            func.count(TeamsTask.id),
            func.sum(case((TeamsTask.status == "completed", 1), else_=0)),
            func.sum(case((TeamsTask.status == "error", 1), else_=0)),
            func.sum(case((TeamsTask.status == "timeout", 1), else_=0)),
        )
        .filter(TeamsTask.created_at >= cutoff)
        .group_by(bucket)
        .order_by(bucket.asc())
        .all()
    )
    out = []
    for b, total, comp, err, tmo in rows:
        out.append({
            "bucket": b.isoformat() if hasattr(b, "isoformat") else str(b),
            "total": int(total),
            "completed": int(comp or 0),
            "error": int(err or 0),
            "timeout": int(tmo or 0),
        })
    return out


def get_recent_tasks(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Drill-down: ultimas tasks (mais recentes primeiro), filtravel por status."""
    from app.teams.models import TeamsTask
    q = TeamsTask.query
    if status:
        q = q.filter(TeamsTask.status == status)
    rows = q.order_by(TeamsTask.created_at.desc()).limit(limit).all()
    out = []
    for t in rows:
        latencia_s = None
        if t.completed_at and t.created_at:
            d = (t.completed_at - t.created_at).total_seconds()
            latencia_s = round(d, 1) if d >= 0 else None
        out.append({
            "id": t.id,
            "conversation_id": t.conversation_id,
            "status": t.status,
            "user_id": t.user_id,
            "user_name": t.user_name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "latencia_s": latencia_s,
            "mensagem_preview": (t.mensagem or "")[:80],
        })
    return out


# ---------------------------------------------------------------------------
# CUSTO / QUALIDADE — agent_step (channel='teams')
# ---------------------------------------------------------------------------

def get_cost_quality_overview(period: str = "7d") -> Dict[str, Any]:
    """Tokens e custo dos turnos do Teams (AgentStep channel='teams') no periodo."""
    from app.agente.models import AgentStep
    from app.agente.config import get_settings
    cutoff = _cutoff(period)
    rows = (
        db.session.query(
            AgentStep.model,
            func.count(AgentStep.id),
            func.coalesce(func.sum(AgentStep.input_tokens), 0),
            func.coalesce(func.sum(AgentStep.output_tokens), 0),
        )
        .filter(AgentStep.channel == "teams", AgentStep.created_at >= cutoff)
        .group_by(AgentStep.model)
        .all()
    )
    settings = get_settings()
    num_turnos = 0
    total_in = 0
    total_out = 0
    custo = 0.0
    por_modelo: Dict[str, Any] = {}
    for model, cnt, sin, sout in rows:
        cnt = int(cnt)
        sin = int(sin or 0)
        sout = int(sout or 0)
        num_turnos += cnt
        total_in += sin
        total_out += sout
        try:
            c = float(settings.calculate_cost(sin, sout, model=model or ""))
        except Exception:
            c = 0.0
        custo += c
        por_modelo[model or "desconhecido"] = {
            "turnos": cnt, "input_tokens": sin,
            "output_tokens": sout, "custo_usd": round(c, 4),
        }
    return {
        "period": period,
        "num_turnos": num_turnos,
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "custo_estimado_usd": round(custo, 4),
        "custo_medio_turno_usd": round(custo / num_turnos, 4) if num_turnos else 0.0,
        "por_modelo": por_modelo,
    }


def get_tools_usage(period: str = "7d", limit: int = 15) -> List[Dict[str, Any]]:
    """Ferramentas mais usadas em turnos do Teams (de AgentStep.tools_used)."""
    from app.agente.models import AgentStep
    cutoff = _cutoff(period)
    rows = (
        db.session.query(AgentStep.tools_used)
        .filter(
            AgentStep.channel == "teams",
            AgentStep.created_at >= cutoff,
            AgentStep.tools_used.isnot(None),
        )
        .all()
    )
    counter: Counter = Counter()
    for (tools,) in rows:
        if isinstance(tools, list):
            for t in tools:
                if t:
                    counter[str(t)] += 1
    return [{"tool": name, "count": cnt} for name, cnt in counter.most_common(limit)]


def get_skill_effectiveness(period: str = "7d", limit: int = 30) -> List[Dict[str, Any]]:
    """Efetividade de skills SO em sessoes do Teams (session_id LIKE 'teams_%')."""
    from app.agente.models import AgentSkillEffectiveness
    cutoff = _cutoff(period)
    resolveu_int = func.sum(
        case((AgentSkillEffectiveness.resolveu.is_(True), 1), else_=0)
    )
    rows = (
        db.session.query(
            AgentSkillEffectiveness.skill_name,
            func.count(AgentSkillEffectiveness.id),
            resolveu_int,
        )
        .filter(
            AgentSkillEffectiveness.session_id.like("teams_%"),
            AgentSkillEffectiveness.created_at >= cutoff,
        )
        .group_by(AgentSkillEffectiveness.skill_name)
        .order_by(func.count(AgentSkillEffectiveness.id).desc())
        .limit(limit)
        .all()
    )
    out = []
    for name, total, resolv in rows:
        total = int(total)
        resolv = int(resolv or 0)
        out.append({
            "skill_name": name,
            "total": total,
            "resolveu": resolv,
            "taxa_resolucao": round(100.0 * resolv / total, 1) if total else 0.0,
        })
    return out
