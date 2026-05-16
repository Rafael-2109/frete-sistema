-- Migration: agent_invocation_metrics (A1 — telemetria per-subagent)
-- Data: 2026-05-16
-- Ref: app/agente/sdk/hooks.py:_subagent_stop_hook
-- Roadmap: .claude/references/STUDY_PROMPT_ENGINEERING_2026.md (Fase A — Instrumentacao)
--
-- Tabela para persistir UMA LINHA POR INVOCACAO de subagent. Granularidade
-- distinta de agent_session_costs (que e per-message do CostTracker).
-- Aqui cada linha representa um spawn->stop completo de subagent.
--
-- Habilitado via flag AGENT_INVOCATION_METRICS_PERSIST=true. Quando off,
-- hook continua extraindo dados mas NAO persiste (rollback trivial).
--
-- Foreign keys: SEM FK explicita para agent_sessions.session_id porque
-- sessoes podem ser deletadas (cascade) e queremos preservar metricas
-- historicas para analise de regressao cross-deploy. Mesmo padrao de
-- agent_session_costs (2026-05-09).
--
-- Idempotente via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS agent_invocation_metrics (
  id              BIGSERIAL PRIMARY KEY,
  agent_id        TEXT NOT NULL,
  agent_type      TEXT NOT NULL,
  session_id      TEXT NULL,
  user_id         INTEGER NULL,
  started_at      TIMESTAMP NULL,
  finished_at     TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
  duration_ms     INTEGER NULL,
  num_turns       INTEGER NULL,
  stop_reason     TEXT NULL,
  cost_usd        NUMERIC(10, 6) NULL,
  input_tokens          INTEGER NOT NULL DEFAULT 0,
  output_tokens         INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
  cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
  escalated_to_human       BOOLEAN NOT NULL DEFAULT FALSE,
  user_correction_received BOOLEAN NULL,
  source          TEXT NOT NULL DEFAULT 'production',
  recorded_at     TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- Deduplicacao por agent_id (SDK reuse possivel em retry — idempotente)
CREATE UNIQUE INDEX IF NOT EXISTS agent_invocation_metrics_agent_id_uniq
  ON agent_invocation_metrics (agent_id);

-- Query principal do dashboard: por agent_type ao longo do tempo
CREATE INDEX IF NOT EXISTS agent_invocation_metrics_type_recorded_idx
  ON agent_invocation_metrics (agent_type, recorded_at DESC);

-- Query secundaria: por usuario (analise de uso por Rafael/equipe)
CREATE INDEX IF NOT EXISTS agent_invocation_metrics_user_recorded_idx
  ON agent_invocation_metrics (user_id, recorded_at DESC)
  WHERE user_id IS NOT NULL;

-- Query terciaria: por sessao (debug / co-ocorrencia)
CREATE INDEX IF NOT EXISTS agent_invocation_metrics_session_idx
  ON agent_invocation_metrics (session_id)
  WHERE session_id IS NOT NULL;

-- Janela temporal global (cleanup / retencao)
CREATE INDEX IF NOT EXISTS agent_invocation_metrics_recorded_idx
  ON agent_invocation_metrics (recorded_at DESC);

COMMENT ON TABLE agent_invocation_metrics IS
  'A1 (2026-05-16): telemetria per-invocacao de subagent. Habilitado via flag '
  'AGENT_INVOCATION_METRICS_PERSIST. Sem FK para agent_sessions — preserva '
  'historico apos cascade delete. Granularidade distinta de agent_session_costs '
  '(que e per-message). source=production|dev distingue Claude Code CLI vs agente web.';
