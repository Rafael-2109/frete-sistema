-- Migration E2 (2026-04-19) — FK linha_original_id em carvia_extrato_linhas
-- (detecta pares de estorno OFX).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_e2_linha_original_id.sql

BEGIN;

ALTER TABLE carvia_extrato_linhas
    ADD COLUMN IF NOT EXISTS linha_original_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_carvia_extrato_linha_original'
          AND table_name = 'carvia_extrato_linhas'
    ) THEN
        ALTER TABLE carvia_extrato_linhas
            ADD CONSTRAINT fk_carvia_extrato_linha_original
            FOREIGN KEY (linha_original_id)
            REFERENCES carvia_extrato_linhas(id)
            ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_carvia_extrato_linhas_linha_original
    ON carvia_extrato_linhas (linha_original_id);

COMMIT;
