-- Migration E3 (2026-04-19) — valor_acrescimo / valor_desconto em
-- carvia_conciliacoes (juros, multa, desconto em pagamento).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_e3_juros_desconto.sql

BEGIN;

ALTER TABLE carvia_conciliacoes
    ADD COLUMN IF NOT EXISTS valor_acrescimo NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS valor_desconto  NUMERIC(15, 2);

COMMIT;
