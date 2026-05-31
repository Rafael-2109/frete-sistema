-- Migration: D3 — Fatos bi-temporais + proveniência no Knowledge Graph
-- Tabelas: agent_memory_entity_relations, agent_memory_entity_links
--
-- Idempotente via IF NOT EXISTS.
-- Aplicar em Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/2026_05_31_kg_bitemporal.sql
--
-- Semântica das novas colunas:
--   valid_from        — quando o fato entrou em vigor (tempo do mundo real; NULL = desconhecido)
--   valid_to          — quando o fato expirou (NULL = ainda vigente; MVP: sempre NULL)
--   source_session_id — sessão de origem da relação/link (texto, FK soft para agent_sessions)
--   source_step_uid   — step de origem (texto, FK soft para agent_step.step_uid; NULL por ora)
--
-- Decisão ON CONFLICT: preservar a 1ª origem (source_session_id/source_step_uid do INSERT
-- original). A cláusula DO UPDATE em _upsert_relation usa COALESCE(existing, excluded),
-- portanto o 1º escritor vence e re-upserts não sobrescrevem a proveniência original.

ALTER TABLE agent_memory_entity_relations
  ADD COLUMN IF NOT EXISTS valid_from        TIMESTAMP NULL,
  ADD COLUMN IF NOT EXISTS valid_to          TIMESTAMP NULL,
  ADD COLUMN IF NOT EXISTS source_session_id TEXT NULL,
  ADD COLUMN IF NOT EXISTS source_step_uid   TEXT NULL;

ALTER TABLE agent_memory_entity_links
  ADD COLUMN IF NOT EXISTS source_session_id TEXT NULL,
  ADD COLUMN IF NOT EXISTS source_step_uid   TEXT NULL;
