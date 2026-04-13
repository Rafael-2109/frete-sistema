-- Migration: renomear FC_VIRTUAL -> MANUAL + adicionar conta_origem
-- Refatoracao W10 Nivel 2 — Sprint 4 followup (auditoria CarVia)
-- Idempotente — safe para rodar no Render Shell.
--
-- Muda:
--   1. DROP CHECK antigo (que aceita FC_VIRTUAL)
--   2. UPDATE origem FC_VIRTUAL -> MANUAL
--   3. ADD COLUMN conta_origem VARCHAR(100)
--   4. Backfill conta_origem='(a informar)' em linhas MANUAL
--   5. UPDATE arquivo_ofx FC_VIRTUAL -> MANUAL (consistencia)
--   6. ADD CHECK novo (OFX | CSV | MANUAL)
--   7. ADD CHECK partial ck_carvia_extrato_manual_conta
--      (origem != 'MANUAL' OR conta_origem IS NOT NULL)
--      CRITICO: rodar APOS backfill (step 4) — senao falha em linhas pre-existentes.

-- 1. DROP CHECK antigo (idempotente via IF EXISTS)
ALTER TABLE carvia_extrato_linhas
    DROP CONSTRAINT IF EXISTS ck_carvia_extrato_origem;

-- 2. UPDATE origem FC_VIRTUAL -> MANUAL
UPDATE carvia_extrato_linhas
   SET origem = 'MANUAL'
 WHERE origem = 'FC_VIRTUAL';

-- 3. ADD COLUMN conta_origem (idempotente)
ALTER TABLE carvia_extrato_linhas
    ADD COLUMN IF NOT EXISTS conta_origem VARCHAR(100) NULL;

-- 4. Backfill conta_origem em linhas MANUAL sem valor
UPDATE carvia_extrato_linhas
   SET conta_origem = '(a informar)'
 WHERE origem = 'MANUAL'
   AND (conta_origem IS NULL OR conta_origem = '');

-- 5. UPDATE arquivo_ofx FC_VIRTUAL -> MANUAL (consistencia)
UPDATE carvia_extrato_linhas
   SET arquivo_ofx = 'MANUAL'
 WHERE arquivo_ofx = 'FC_VIRTUAL';

-- 6. ADD CHECK novo com valores validos OFX|CSV|MANUAL
--    (DO block para idempotencia — CREATE CONSTRAINT nao tem IF NOT EXISTS)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'carvia_extrato_linhas'
          AND constraint_name = 'ck_carvia_extrato_origem'
    ) THEN
        ALTER TABLE carvia_extrato_linhas
            ADD CONSTRAINT ck_carvia_extrato_origem
            CHECK (origem IN ('OFX', 'CSV', 'MANUAL'));
    END IF;
END $$;

-- 7. ADD CHECK partial ck_carvia_extrato_manual_conta — enforcement DB
--    (origem != 'MANUAL' OR conta_origem IS NOT NULL)
--    CRITICO: roda APOS backfill (step 4) — senao falha em linhas
--    MANUAL pre-existentes com conta_origem NULL.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'carvia_extrato_linhas'
          AND constraint_name = 'ck_carvia_extrato_manual_conta'
    ) THEN
        ALTER TABLE carvia_extrato_linhas
            ADD CONSTRAINT ck_carvia_extrato_manual_conta
            CHECK (origem != 'MANUAL' OR conta_origem IS NOT NULL);
    END IF;
END $$;

-- Verificacao (read-only)
SELECT origem, COUNT(*) FROM carvia_extrato_linhas
GROUP BY origem ORDER BY origem;

SELECT column_name, data_type, character_maximum_length
  FROM information_schema.columns
 WHERE table_name = 'carvia_extrato_linhas'
   AND column_name IN ('origem', 'conta_origem');

SELECT conname, pg_get_constraintdef(oid) AS check_constraint
  FROM pg_constraint
 WHERE conname IN (
    'ck_carvia_extrato_origem',
    'ck_carvia_extrato_manual_conta'
 )
 ORDER BY conname;
