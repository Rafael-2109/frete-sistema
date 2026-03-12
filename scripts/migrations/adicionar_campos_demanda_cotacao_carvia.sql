-- Migration: Adicionar valor_proposto e valor_contra_proposta em carvia_sessao_demandas
-- Idempotente — seguro para executar multiplas vezes

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_sessao_demandas'
        AND column_name = 'valor_proposto'
    ) THEN
        ALTER TABLE carvia_sessao_demandas
            ADD COLUMN valor_proposto NUMERIC(15,2);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_sessao_demandas'
        AND column_name = 'valor_contra_proposta'
    ) THEN
        ALTER TABLE carvia_sessao_demandas
            ADD COLUMN valor_contra_proposta NUMERIC(15,2);
    END IF;
END $$;
