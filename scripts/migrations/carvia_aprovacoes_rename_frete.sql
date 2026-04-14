-- Migration: Rename carvia_aprovacoes_subcontrato → carvia_aprovacoes_frete
-- Trocar FK subcontrato_id → frete_id. Data: 2026-04-14
-- Idempotente: re-run seguro (skip se tabela ja renomeada).

-- 0. Idempotency guard — skip all se migration ja rodou
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'carvia_aprovacoes_subcontrato'
  ) THEN
    RAISE NOTICE 'Migration ja aplicada (tabela carvia_aprovacoes_subcontrato nao existe). Saltando.';
    RETURN;
  END IF;

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

  -- 3. Abortar se orfaos (data loss prevention)
  DECLARE orfaos INT;
  BEGIN
    SELECT COUNT(*) INTO orfaos
    FROM carvia_aprovacoes_subcontrato
    WHERE frete_id IS NULL;
    IF orfaos > 0 THEN
      RAISE EXCEPTION
        'ABORT: % aprovacoes orfas (sem frete_id apos backfill). '
        'Data loss prevention — investigar manualmente antes de prosseguir. '
        'Query: SELECT * FROM carvia_aprovacoes_subcontrato WHERE frete_id IS NULL',
        orfaos;
    END IF;
  END;

  -- 4. NOT NULL em frete_id (agora seguro — sem orfaos)
  ALTER TABLE carvia_aprovacoes_subcontrato
    ALTER COLUMN frete_id SET NOT NULL;

  -- 5. Index em frete_id
  CREATE INDEX IF NOT EXISTS idx_carvia_aprovacoes_frete_id
    ON carvia_aprovacoes_subcontrato (frete_id);

  -- 6. Renomear tabela
  ALTER TABLE carvia_aprovacoes_subcontrato
    RENAME TO carvia_aprovacoes_frete;

  -- 7. DROP coluna subcontrato_id (apos rename)
  ALTER TABLE carvia_aprovacoes_frete
    DROP COLUMN IF EXISTS subcontrato_id;

  RAISE NOTICE 'Migration carvia_aprovacoes_rename_frete concluida.';
END $$;
