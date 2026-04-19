-- Migration A1 (2026-04-17) — adiciona cte_complementar_id em
-- carvia_fatura_cliente_itens.
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_fatura_cliente_item_cte_complementar_id.sql

BEGIN;

-- Coluna (idempotente)
ALTER TABLE carvia_fatura_cliente_itens
    ADD COLUMN IF NOT EXISTS cte_complementar_id INTEGER;

-- FK (idempotente)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_fatura_item_cte_complementar'
          AND table_name = 'carvia_fatura_cliente_itens'
    ) THEN
        ALTER TABLE carvia_fatura_cliente_itens
            ADD CONSTRAINT fk_fatura_item_cte_complementar
            FOREIGN KEY (cte_complementar_id)
            REFERENCES carvia_cte_complementares(id)
            ON DELETE SET NULL;
    END IF;
END
$$;

-- Index (idempotente)
CREATE INDEX IF NOT EXISTS
    ix_carvia_fatura_cliente_itens_cte_complementar_id
    ON carvia_fatura_cliente_itens (cte_complementar_id);

COMMIT;
