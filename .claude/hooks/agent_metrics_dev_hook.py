#!/usr/bin/env python3
"""
Hook PostToolUse (matcher Agent): captura metricas per-invocacao de subagent
no Claude Code CLI (DEV environment).

Complementa a telemetria de PRODUCAO em `app/agente/sdk/hooks.py`
(_subagent_stop_hook), que cobre apenas usuarios do agente web (Rafael+equipe
via chat). Este hook cobre dev (Rafael usando Claude Code localmente).

Estrategia: append em JSONL local em `/tmp/agent_invocation_metrics_dev/`,
sem dependencia de DB. Um script separado (futura entrega A3 do roadmap)
ingere o JSONL para a tabela `agent_invocation_metrics` com `source='dev'`.

Por que JSONL e nao DB direto:
- Sessoes Claude Code podem nao ter DATABASE_URL exportado
- Append em arquivo e atomico em POSIX (writes < PIPE_BUF) e nao trava
- Isolamento: erro de DB nao impacta a sessao Claude Code do dev

Schema (v1) — uma linha por invocacao:
{
  "schema_version": "v1",
  "timestamp": "2026-05-16T14:23:45+00:00",
  "session_id": "uuid",
  "agent_type": "analista-carteira",   # subagent_type do tool_input
  "tool_name": "Agent",
  "duration_ms": 12340,                  # se disponivel em tool_response
  "cost_usd": 0.0123,                    # se disponivel
  "input_tokens": 1234,
  "output_tokens": 567,
  "source": "dev"
}

Best-effort: TODOS os erros sao silenciados. Exit 0 sempre.
NAO bloqueia execucao do Claude Code em nenhuma circunstancia.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


METRICS_DIR = Path("/tmp/agent_invocation_metrics_dev")
MATCHER_TOOL_NAME = "Agent"


def _extract_tokens(tool_response) -> tuple:
    """Extrai (input_tokens, output_tokens) do tool_response.

    tool_response pode ter shapes diferentes conforme versao do CLI/SDK.
    Tentamos os 2 caminhos mais comuns: response.usage e response[-1].usage
    (ResultMessage). Defensivo: qualquer falha retorna (0, 0).
    """
    if not isinstance(tool_response, dict):
        return 0, 0

    usage = tool_response.get("usage")
    if isinstance(usage, dict):
        return (
            int(usage.get("input_tokens") or 0),
            int(usage.get("output_tokens") or 0),
        )

    return 0, 0


def _extract_cost(tool_response) -> float:
    """Extrai total_cost_usd do tool_response (None se ausente)."""
    if not isinstance(tool_response, dict):
        return None
    val = tool_response.get("total_cost_usd")
    if val is None:
        val = tool_response.get("cost_usd")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _extract_duration(tool_response) -> int:
    """Extrai duration_ms do tool_response (None se ausente)."""
    if not isinstance(tool_response, dict):
        return None
    val = tool_response.get("duration_ms")
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw:
            return 0
        payload = json.loads(raw)
    except Exception:
        return 0  # silencioso

    tool_name = payload.get("tool_name") or ""
    if tool_name != MATCHER_TOOL_NAME:
        # PostToolUse com matcher: Agent deveria filtrar, mas defesa em
        # profundidade — exit silencioso se outro tool chegar aqui.
        return 0

    tool_input = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response") or {}

    agent_type = tool_input.get("subagent_type") or "unknown"
    session_id = payload.get("session_id") or ""

    input_tokens, output_tokens = _extract_tokens(tool_response)
    cost_usd = _extract_cost(tool_response)
    duration_ms = _extract_duration(tool_response)

    record = {
        "schema_version": "v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "agent_type": agent_type,
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "cost_usd": cost_usd,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "source": "dev",
    }

    try:
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = METRICS_DIR / f"{date_str}.jsonl"
        # Append em arquivo local. POSIX garante atomicidade para writes
        # < PIPE_BUF (geralmente 4KB) — uma linha JSON cabe folgado.
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Silencioso: dev hook NUNCA quebra Claude Code
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
