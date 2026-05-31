-- Migration: agent_step (Onda 0 — fundação física de passo/turno)
-- Data: 2026-05-30
-- Ref: app/agente/models.py (AgentStep)
--
-- Tabela para persistir um registro por TURNO (par user→assistant) do agente.
-- Chave UNIQUE step_uid = "{session_id}:{turn_seq}".
-- Fundação que destrava 3 eixos do blueprint: flywheel, qualidade, planejador.
--
-- Sem FK para agent_sessions — preserva histórico mesmo após cascade delete
-- de sessão (mesma filosofia de agent_session_costs).
--
-- Idempotente via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS agent_step (
  id                      BIGSERIAL PRIMARY KEY,
  step_uid                TEXT NOT NULL,
  session_id              TEXT NULL,
  user_id                 INTEGER NULL,
  channel                 TEXT NULL,
  model                   TEXT NULL,
  input_tokens            INTEGER NOT NULL DEFAULT 0,
  output_tokens           INTEGER NOT NULL DEFAULT 0,
  tools_used              JSONB NULL,
  outcome_signal          JSONB NULL,
  outcome_effective_count INTEGER NULL,
  created_at              TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- Chave de deduplicação: "{session_id}:{turn_seq}"
CREATE UNIQUE INDEX IF NOT EXISTS agent_step_step_uid_uniq
  ON agent_step (step_uid);

-- Query principal: steps por sessão (histórico de turnos)
CREATE INDEX IF NOT EXISTS agent_step_session_id_idx
  ON agent_step (session_id)
  WHERE session_id IS NOT NULL;

-- Filtro por usuário (dashboard / flywheel)
CREATE INDEX IF NOT EXISTS agent_step_user_id_idx
  ON agent_step (user_id)
  WHERE user_id IS NOT NULL;

-- Janela temporal global (retenção / cleanup)
-- NOTA: sem partial predicate (WHERE ... IS NOT NULL) porque created_at é
-- NOT NULL — todas as linhas são indexáveis. NÃO adicionar predicate aqui
-- (diferente de session_id/user_id, que são nullable).
CREATE INDEX IF NOT EXISTS agent_step_created_at_idx
  ON agent_step (created_at DESC);

COMMENT ON TABLE agent_step IS
  'Onda 0 (2026-05-30): entidade de passo/turno do agente. '
  '1 registro por par user→assistant. step_uid = session_id:turn_seq. '
  'Sem FK para agent_sessions — preserva histórico após cascade delete. '
  'outcome_signal e outcome_effective_count preenchidos na Onda 1.';
