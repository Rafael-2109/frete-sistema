-- Migration: agent_eval_scores (A3 Fase 1 — baseline de eval por-agente)
-- Data: 2026-05-31
-- Ref: app/agente/models.py (AgentEvalScore), app/agente/services/eval_gate_service.py
--
-- Tabela para persistir o score de eval (passed/total) por agent_name.
-- Substitui o `baseline_score=0.0` hardcoded no eval gate (módulo 28 do
-- scheduler). O baseline contra o qual o run atual compara (report-only,
-- e enforce futuro) é o `score` do run ANTERIOR mais recente do mesmo
-- agent_name (ORDER BY recorded_at DESC LIMIT 1).
--
-- Sem FK para agent_sessions — preserva histórico de scores cross-deploy
-- para análise de regressão (mesma filosofia de agent_invocation_metrics).
--
-- Idempotente via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS agent_eval_scores (
  id           BIGSERIAL PRIMARY KEY,
  agent_name   TEXT NOT NULL,
  score        DOUBLE PRECISION NOT NULL,
  total        INTEGER NOT NULL DEFAULT 0,
  passed       INTEGER NOT NULL DEFAULT 0,
  git_sha      TEXT NULL,
  mode         TEXT NULL,
  recorded_at  TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- Filtro principal: scores por agent_name (lookup do baseline)
CREATE INDEX IF NOT EXISTS agent_eval_scores_agent_name_idx
  ON agent_eval_scores (agent_name);

-- Janela temporal global + baseline lookup (ORDER BY recorded_at DESC).
-- NOTA: sem partial predicate porque recorded_at é NOT NULL.
CREATE INDEX IF NOT EXISTS agent_eval_scores_recorded_at_idx
  ON agent_eval_scores (recorded_at DESC);

COMMENT ON TABLE agent_eval_scores IS
  'A3 Fase 1 (2026-05-31): baseline de eval por-agente para o eval gate. '
  '1 linha por run (score = passed/total). Baseline = score do run anterior '
  'mais recente do mesmo agent_name. Report-only inicialmente (mode), enforce '
  'futuro. Sem FK — preserva histórico cross-deploy. Substitui baseline_score=0.0 '
  'hardcoded em eval_gate_service (módulo 28 do scheduler).';
