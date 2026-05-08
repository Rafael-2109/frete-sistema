-- UNIQUE (recibo_id, chassi) — protege contra race em conferência simultânea.
-- Já criado no Plano 1 schema (verificar se existe; idempotente).

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'assai_recibo_item'
          AND indexname = 'ux_assai_recibo_item_recibo_chassi'
    ) THEN
        CREATE UNIQUE INDEX ux_assai_recibo_item_recibo_chassi
            ON assai_recibo_item(recibo_id, chassi);
    END IF;
END $$;
