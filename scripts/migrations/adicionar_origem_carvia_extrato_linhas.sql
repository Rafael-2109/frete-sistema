-- Migration: CarviaExtratoLinha.origem (W10 Nivel 2)
-- Adiciona coluna origem para distinguir linhas reais de virtuais (FC).
-- Idempotente — safe para rodar no Render Shell.

-- 1. Adicionar coluna com default 'OFX' para backfill automatico
ALTER TABLE carvia_extrato_linhas
    ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'OFX';

-- 2. Indice para filtros por origem
CREATE INDEX IF NOT EXISTS ix_carvia_extrato_origem
    ON carvia_extrato_linhas (origem);

-- 3. CHECK constraint para valores validos
-- (DO block para idempotencia — CREATE CONSTRAINT nao tem IF NOT EXISTS)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'carvia_extrato_linhas'
          AND constraint_name = 'ck_carvia_extrato_origem'
    ) THEN
        ALTER TABLE carvia_extrato_linhas
            ADD CONSTRAINT ck_carvia_extrato_origem
            CHECK (origem IN ('OFX', 'CSV', 'FC_VIRTUAL'));
    END IF;
END $$;

-- Verificacao (apenas SELECT — nao modifica nada)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'carvia_extrato_linhas' AND column_name = 'origem';

SELECT origem, COUNT(*)
FROM carvia_extrato_linhas
GROUP BY origem
ORDER BY origem;
