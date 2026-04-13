-- ========================================================================
-- Migration: adicionar fatura_transportadora_id em carvia_custos_entrega
-- ========================================================================
-- Replica o padrao DespesaExtra.fatura_frete_id do Nacom no CarVia.
-- Permite vincular CarviaCustoEntrega diretamente a CarviaFaturaTransportadora.
--
-- IMPORTANTE: idempotente, seguro para re-execucao.
-- NAO remove subcontrato_id — migration destructive sera separada.
-- ========================================================================

-- 1. ADD COLUMN
ALTER TABLE carvia_custos_entrega
  ADD COLUMN IF NOT EXISTS fatura_transportadora_id INTEGER NULL;

-- 2. ADD FOREIGN KEY (ON DELETE SET NULL)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'carvia_custos_entrega'
          AND constraint_name = 'fk_ce_fatura_transportadora'
    ) THEN
        ALTER TABLE carvia_custos_entrega
          ADD CONSTRAINT fk_ce_fatura_transportadora
          FOREIGN KEY (fatura_transportadora_id)
          REFERENCES carvia_faturas_transportadora(id)
          ON DELETE SET NULL;
    END IF;
END $$;

-- 3. CREATE INDEX
CREATE INDEX IF NOT EXISTS ix_carvia_custos_entrega_fatura_transportadora_id
  ON carvia_custos_entrega(fatura_transportadora_id);

-- 4. BACKFILL: propagar fatura_transportadora_id via subcontrato_id legado
UPDATE carvia_custos_entrega ce
SET fatura_transportadora_id = sub.fatura_transportadora_id
FROM carvia_subcontratos sub
WHERE ce.subcontrato_id = sub.id
  AND sub.fatura_transportadora_id IS NOT NULL
  AND ce.fatura_transportadora_id IS NULL;

-- 5. BACKFILL status: PENDENTE -> VINCULADO_FT para CEs com FT nova
UPDATE carvia_custos_entrega
SET status = 'VINCULADO_FT'
WHERE fatura_transportadora_id IS NOT NULL
  AND status = 'PENDENTE';

-- 6. Relatorio: CEs com subcontrato_id mas sem fatura_transportadora_id (orfaos)
SELECT
    'CEs com subcontrato_id sem FT (revisar manualmente)' AS aviso,
    COUNT(*) AS total
FROM carvia_custos_entrega ce
WHERE ce.subcontrato_id IS NOT NULL
  AND ce.fatura_transportadora_id IS NULL;

-- 7. Resumo
SELECT
    COUNT(*) AS total_ces,
    COUNT(*) FILTER (WHERE fatura_transportadora_id IS NOT NULL) AS com_ft,
    COUNT(*) FILTER (WHERE status = 'VINCULADO_FT') AS vinculado_ft,
    COUNT(*) FILTER (WHERE status = 'PAGO') AS pago,
    COUNT(*) FILTER (WHERE status = 'PENDENTE') AS pendente,
    COUNT(*) FILTER (WHERE status = 'CANCELADO') AS cancelado
FROM carvia_custos_entrega;
