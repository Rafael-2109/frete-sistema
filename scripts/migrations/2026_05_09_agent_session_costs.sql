-- Migration: agent_session_costs (F8 — cost tracker persistente)
-- Data: 2026-05-09
-- Ref: app/agente/sdk/cost_tracker.py
--
-- Tabela para persistir entradas de custo do CostTracker em DB, mantendo
-- historico cross-deploy. Hoje cost_tracker eh runtime-only (perde dados ao
-- redeploy do worker/web). Quando flag AGENT_COST_TRACKER_PERSIST=true,
-- record_cost() faz write-through aqui.
--
-- Idempotente via IF NOT EXISTS.
-- Foreign keys: SEM FK explicita para agent_sessions.session_id porque sessoes
-- podem ser deletadas (cascade) e queremos preservar custo historico para
-- relatorios financeiros (auditoria). Caller eh responsavel por filtrar
-- session_id orfaos se quiser.

CREATE TABLE IF NOT EXISTS agent_session_costs (
  id              BIGSERIAL PRIMARY KEY,
  message_id      TEXT NOT NULL,
  session_id      TEXT NULL,
  user_id         INTEGER NULL,
  tool_name       TEXT NULL,
  model           TEXT NULL,
  input_tokens    INTEGER NOT NULL DEFAULT 0,
  output_tokens   INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
  cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
  cost_usd        NUMERIC(10, 6) NOT NULL DEFAULT 0,
  recorded_at     TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- Unique: deduplicar por message_id (mesma logica de _seen_message_ids in-memory)
CREATE UNIQUE INDEX IF NOT EXISTS agent_session_costs_message_id_uniq
  ON agent_session_costs (message_id);

-- Query principal: filtro por user + janela temporal (dashboard insights)
CREATE INDEX IF NOT EXISTS agent_session_costs_user_recorded_idx
  ON agent_session_costs (user_id, recorded_at DESC)
  WHERE user_id IS NOT NULL;

-- Query secundaria: custo por sessao (debug + relatorios)
CREATE INDEX IF NOT EXISTS agent_session_costs_session_idx
  ON agent_session_costs (session_id)
  WHERE session_id IS NOT NULL;

-- Janela temporal global (para retencao / cleanup)
CREATE INDEX IF NOT EXISTS agent_session_costs_recorded_idx
  ON agent_session_costs (recorded_at DESC);

COMMENT ON TABLE agent_session_costs IS
  'F8 (2026-05-09): persistencia de cost_tracker entries. Habilitado via flag '
  'AGENT_COST_TRACKER_PERSIST. Sem FK para agent_sessions — preserva historico '
  'mesmo apos cascade delete de sessao. Caller filtra orfaos quando necessario.';
