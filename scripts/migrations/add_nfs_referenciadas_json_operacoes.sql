-- ==========================================================================
-- Migration: ADD nfs_referenciadas_json TO carvia_operacoes
-- ==========================================================================
--
-- Armazena as referencias de NF extraidas do CTe XML como JSONB.
-- Permite re-linking retroativo quando NF e importada APOS o CTe.
--
-- Formato:
-- [
--   {"chave": "44digitos", "numero_nf": "33268", "cnpj_emitente": "12345678000199"},
--   ...
-- ]
--
-- Idempotente: usa IF NOT EXISTS.
--
-- Execucao no Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/add_nfs_referenciadas_json_operacoes.sql
-- ==========================================================================

-- 1. Adicionar coluna (idempotente)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_operacoes'
          AND column_name = 'nfs_referenciadas_json'
    ) THEN
        ALTER TABLE carvia_operacoes
        ADD COLUMN nfs_referenciadas_json JSONB;
        RAISE NOTICE 'Coluna nfs_referenciadas_json CRIADA em carvia_operacoes';
    ELSE
        RAISE NOTICE 'Coluna nfs_referenciadas_json ja existe em carvia_operacoes';
    END IF;
END $$;

-- 2. Verificacao
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'carvia_operacoes'
  AND column_name = 'nfs_referenciadas_json';
