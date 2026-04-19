-- Migration D2 (2026-04-19) — FKs opcionais operacao_id/frete_id em
-- carvia_despesas. Permite vincular despesa a CTe/frete especifico
-- (ex: seguro de 1 operacao).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_d2_despesa_fks.sql

BEGIN;

ALTER TABLE carvia_despesas
    ADD COLUMN IF NOT EXISTS operacao_id INTEGER,
    ADD COLUMN IF NOT EXISTS frete_id    INTEGER;

-- FK operacao_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_carvia_despesas_operacao'
          AND table_name = 'carvia_despesas'
    ) THEN
        ALTER TABLE carvia_despesas
            ADD CONSTRAINT fk_carvia_despesas_operacao
            FOREIGN KEY (operacao_id)
            REFERENCES carvia_operacoes(id)
            ON DELETE SET NULL;
    END IF;
END
$$;

-- FK frete_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_carvia_despesas_frete'
          AND table_name = 'carvia_despesas'
    ) THEN
        ALTER TABLE carvia_despesas
            ADD CONSTRAINT fk_carvia_despesas_frete
            FOREIGN KEY (frete_id)
            REFERENCES carvia_fretes(id)
            ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_carvia_despesas_operacao_id
    ON carvia_despesas (operacao_id);
CREATE INDEX IF NOT EXISTS ix_carvia_despesas_frete_id
    ON carvia_despesas (frete_id);

COMMIT;
