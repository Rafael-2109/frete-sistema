-- Migration: drop agent_sessions.sdk_session_transcript (SessionStore Fase C)
-- Data: 2026-04-21
-- Ref: app/agente/CLAUDE.md secao "Fase C (cleanup, opcional)"
--
-- Pos SessionStore Fase B cutover (2026-04-21): coluna TEXT 1GB nao tem mais
-- callers operacionais. `save_transcript()` / `get_transcript()` em models.py
-- nunca sao chamados. `session_has_legacy_transcript()` em session_store_adapter.py
-- apenas checava existencia para logica de dual-run (removida em Fase B).
--
-- session_turn_indexer.py usa defer() para nao carregar — remover defer tambem.
--
-- Ganho estimado: ~66MB + remocao de coluna confusa.
--
-- Idempotente via IF EXISTS.

ALTER TABLE agent_sessions
  DROP COLUMN IF EXISTS sdk_session_transcript;
