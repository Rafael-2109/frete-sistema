-- Migration F1 (2026-04-19) — eh_compensacao + compensacao_motivo em
-- carvia_conciliacoes (encontro de contas cross-tipo).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_f1_compensacao.sql

BEGIN;

ALTER TABLE carvia_conciliacoes
    ADD COLUMN IF NOT EXISTS eh_compensacao BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS compensacao_motivo VARCHAR(255);

CREATE INDEX IF NOT EXISTS ix_carvia_conciliacoes_eh_compensacao
    ON carvia_conciliacoes (eh_compensacao)
    WHERE eh_compensacao = TRUE;

COMMIT;
