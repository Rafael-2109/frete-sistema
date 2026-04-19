-- Migration D6 (2026-04-19) — Autoria de DIVERGENTE/EM_CONFERENCIA
-- em CarviaFaturaTransportadora (GAP-32).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_d6_autoria_status.sql

BEGIN;

ALTER TABLE carvia_faturas_transportadora
    ADD COLUMN IF NOT EXISTS divergente_por      VARCHAR(100),
    ADD COLUMN IF NOT EXISTS divergente_em       TIMESTAMP,
    ADD COLUMN IF NOT EXISTS em_conferencia_por  VARCHAR(100),
    ADD COLUMN IF NOT EXISTS em_conferencia_em   TIMESTAMP;

COMMIT;
