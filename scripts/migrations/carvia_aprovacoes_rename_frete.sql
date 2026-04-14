-- Migration: Rename carvia_aprovacoes_subcontrato → carvia_aprovacoes_frete
-- Trocar FK subcontrato_id → frete_id. Data: 2026-04-14

-- 1. Adicionar frete_id nullable
ALTER TABLE carvia_aprovacoes_subcontrato
  ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id);

-- 2. Backfill frete_id via sub.frete_id
UPDATE carvia_aprovacoes_subcontrato aps
SET frete_id = s.frete_id
FROM carvia_subcontratos s
WHERE aps.subcontrato_id = s.id
  AND aps.frete_id IS NULL
  AND s.frete_id IS NOT NULL;

-- 3. Checar orfaos (registros sem frete_id apos backfill)
DO $$
DECLARE
  orfaos INT;
BEGIN
  SELECT COUNT(*) INTO orfaos
  FROM carvia_aprovacoes_subcontrato
  WHERE frete_id IS NULL;
  IF orfaos > 0 THEN
    RAISE NOTICE 'AVISO: % aprovacoes orfas — requer investigacao', orfaos;
  END IF;
END $$;

-- 4. Index em frete_id
CREATE INDEX IF NOT EXISTS idx_carvia_aprovacoes_frete_id
  ON carvia_aprovacoes_subcontrato (frete_id);

-- 5. Renomear tabela
ALTER TABLE IF EXISTS carvia_aprovacoes_subcontrato
  RENAME TO carvia_aprovacoes_frete;

-- 6. DROP coluna subcontrato_id (apos rename)
ALTER TABLE carvia_aprovacoes_frete
  DROP COLUMN IF EXISTS subcontrato_id;

-- 7. NOT NULL em frete_id (ultimo passo — requer que nao haja orfaos)
-- Comentado para permitir revisao manual dos orfaos se houver:
-- ALTER TABLE carvia_aprovacoes_frete
--   ALTER COLUMN frete_id SET NOT NULL;
