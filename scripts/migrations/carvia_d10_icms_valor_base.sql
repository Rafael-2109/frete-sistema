-- Migration D10 (2026-04-19) — Persiste valor absoluto ICMS e base
-- calculo em carvia_operacoes. Habilita D11 (sugestao GNRE via ICMS).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_d10_icms_valor_base.sql

BEGIN;

ALTER TABLE carvia_operacoes
    ADD COLUMN IF NOT EXISTS icms_valor         NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS icms_base_calculo  NUMERIC(15, 2);

-- Index para ordenacao por valor ICMS no modal de custo fiscal (D11)
CREATE INDEX IF NOT EXISTS ix_carvia_operacoes_icms_valor
    ON carvia_operacoes (icms_valor)
    WHERE icms_valor IS NOT NULL;

COMMIT;
