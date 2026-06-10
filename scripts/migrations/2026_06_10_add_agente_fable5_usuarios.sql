-- 2026-06-10: coluna agente_fable5 em usuarios (opt-in Fable 5 por usuario)
-- Idempotente (IF NOT EXISTS) — seguro para Render Shell.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS agente_fable5 BOOLEAN NOT NULL DEFAULT FALSE;
