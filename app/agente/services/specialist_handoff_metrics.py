"""Gate de metrica do piloto de handoff (F1): custo medio/sessao + cache_read
antes vs depois. Fonte: AgentSessionCost.aggregate_summary (principal) +
AgentInvocationMetric (subagente). Spec: gate = custo cai E cache nao infla."""
from __future__ import annotations


def custo_medio_por_sessao(session_ids: list[str]) -> dict:
    from sqlalchemy import func
    from app.agente.models import AgentSessionCost, AgentInvocationMetric
    total, hit_rates, turns = 0.0, [], []
    for sid in session_ids:
        agg = AgentSessionCost.aggregate_summary(session_id=sid)
        total += float(agg.get("total_cost_usd") or 0)
        hit_rates.append(float(agg.get("cache_hit_rate") or 0))
        # num_turns medio das invocacoes da sessao (sinal de re-descoberta).
        nt = (AgentInvocationMetric.query
              .with_entities(func.coalesce(func.avg(AgentInvocationMetric.num_turns), 0))
              .filter(AgentInvocationMetric.session_id == sid).scalar())
        turns.append(float(nt or 0))
    n = len(session_ids) or 1
    return {
        "custo_total": round(total, 4),
        "sessoes": len(session_ids),
        "custo_medio": round(total / n, 4),
        "cache_hit_rate": round(sum(hit_rates) / n, 4) if hit_rates else 0.0,
        "num_turns": round(sum(turns) / n, 2) if turns else 0.0,
    }


def compara_baseline(baseline: dict, atual: dict) -> dict:
    """Gate da spec: custo cai E cache nao regride E num_turns nao sobe (>5% =
    perdeu contexto). `.get()` com default 0.0 — entrada incompleta nao explode.

    GUARD DE AMOSTRA: exige `atual['custo_medio'] > 0`. Sem ele, um `atual`
    degenerado (zero sessao medida -> custo_medio=0) com baseline de cache 0
    passaria o gate (0 < custo_baseline = 'custo caiu' + 0 >= 0 = 'cache ok'),
    aprovando dados INEXISTENTES — o exato failure mode que o gate existe p/ barrar."""
    b_custo, a_custo = baseline.get("custo_medio", 0.0), atual.get("custo_medio", 0.0)
    b_cache, a_cache = baseline.get("cache_hit_rate", 0.0), atual.get("cache_hit_rate", 0.0)
    b_turns, a_turns = baseline.get("num_turns", 0.0), atual.get("num_turns", 0.0)
    delta_custo = round(a_custo - b_custo, 4)
    delta_cache = round(a_cache - b_cache, 4)
    delta_turns = round(a_turns - b_turns, 2)
    passou = (a_custo > 0 and a_custo < b_custo and a_cache >= b_cache
              and delta_turns <= max(b_turns * 0.05, 0.0))
    return {"delta_custo_medio": delta_custo, "delta_cache_hit_rate": delta_cache,
            "delta_num_turns": delta_turns, "passou_gate": passou}


def gate_handoff(baseline_session_ids: list[str],
                 atual_session_ids: list[str]) -> dict:
    """Caller do gate (8b): compoe custo_medio_por_sessao (antes vs depois) e
    compara_baseline numa unica chamada. Entrada = sessoes pre-handoff (multi-spawn)
    vs sessoes pos-handoff (especialista quente). Mede; NAO bloqueia o swap.
    Best-effort: NUNCA propaga excecao (R1 services) — devolve estrutura inerte."""
    try:
        baseline = custo_medio_por_sessao(baseline_session_ids)
        atual = custo_medio_por_sessao(atual_session_ids)
        gate = compara_baseline(baseline, atual)
        return {"baseline": baseline, "atual": atual, "gate": gate}
    except Exception as _err:
        import logging
        logging.getLogger("sistema_fretes").warning(
            f"[handoff_metrics] gate_handoff falhou (ignorado): {_err}")
        return {"baseline": {}, "atual": {}, "gate": {"passou_gate": False},
                "erro": str(_err)}
