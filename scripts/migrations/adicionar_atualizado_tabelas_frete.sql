-- Migration: Adicionar campos atualizado_em e atualizado_por em tabelas_frete
-- Permite rastrear quem e quando atualizou uma tabela de frete
-- Idempotente: usa IF NOT EXISTS

DO $$
BEGIN
    -- atualizado_em: timestamp da ultima atualizacao
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tabelas_frete' AND column_name = 'atualizado_em'
    ) THEN
        ALTER TABLE tabelas_frete ADD COLUMN atualizado_em TIMESTAMP;
    END IF;

    -- atualizado_por: usuario que fez a ultima atualizacao
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tabelas_frete' AND column_name = 'atualizado_por'
    ) THEN
        ALTER TABLE tabelas_frete ADD COLUMN atualizado_por VARCHAR(120);
    END IF;
END $$;
