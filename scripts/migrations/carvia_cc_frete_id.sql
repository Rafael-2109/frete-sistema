-- Migration: Add frete_id em carvia_conta_corrente_transportadoras
-- Data: 2026-04-14

-- 1. Add column nullable
ALTER TABLE carvia_conta_corrente_transportadoras
  ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id);

-- 2. Backfill via subcontrato
UPDATE carvia_conta_corrente_transportadoras cc
SET frete_id = s.frete_id
FROM carvia_subcontratos s
WHERE cc.subcontrato_id = s.id
  AND cc.frete_id IS NULL
  AND s.frete_id IS NOT NULL;

-- 3. Checar orfaos
DO $$
DECLARE orfaos INT;
BEGIN
  SELECT COUNT(*) INTO orfaos
  FROM carvia_conta_corrente_transportadoras
  WHERE frete_id IS NULL;
  IF orfaos > 0 THEN
    RAISE NOTICE 'AVISO: % movimentacoes CC orfas', orfaos;
  END IF;
END $$;

-- 4. Afrouxar subcontrato_id NOT NULL (modelo Python ja afrouxado em Phase 5).
-- Necessario porque codigo novo nao passa subcontrato_id em INSERTs.
ALTER TABLE carvia_conta_corrente_transportadoras
  ALTER COLUMN subcontrato_id DROP NOT NULL;

-- 5. Index
CREATE INDEX IF NOT EXISTS idx_carvia_cc_frete_id
  ON carvia_conta_corrente_transportadoras (frete_id);

-- 6. DROP subcontrato_id + compensacao_subcontrato_id sera feito pela
-- migration Phase 14 (carvia_drop_sub_conferencia_fields).
