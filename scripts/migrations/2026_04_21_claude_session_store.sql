-- Migration: claude_session_store (SessionStore v0.1.64 — Fase A dual-run)
-- Data: 2026-04-21
-- Ref: examples/session_stores/postgres_session_store.py (anthropics/claude-agent-sdk-python)
--
-- Tabela backend para PostgresSessionStore adapter.
-- Schema OFICIAL do reference adapter — NAO modificar sem revisar conformance.
--
-- Chaves criticas:
-- - subpath=''  (empty string) e sentinel para main transcript; '' != NULL em PK
-- - seq bigserial ordena entries dentro de (project_key, session_id, subpath)
-- - Index parcial WHERE subpath='' mantem list_sessions barato
-- - mtime bigint = epoch-ms UTC (conformance valida > 1e12)
--
-- Idempotente via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS claude_session_store (
  project_key text   NOT NULL,
  session_id  text   NOT NULL,
  subpath     text   NOT NULL DEFAULT '',
  seq         bigserial,
  entry       jsonb  NOT NULL,
  mtime       bigint NOT NULL,
  PRIMARY KEY (project_key, session_id, subpath, seq)
);

CREATE INDEX IF NOT EXISTS claude_session_store_list_idx
  ON claude_session_store (project_key, session_id)
  WHERE subpath = '';

COMMENT ON TABLE claude_session_store IS
  'SessionStore v0.1.64 backend (Fase A dual-run). Uma linha por entry. Mantido pelo SDK via TranscriptMirrorBatcher. Schema oficial do examples/session_stores/postgres_session_store.py.';
