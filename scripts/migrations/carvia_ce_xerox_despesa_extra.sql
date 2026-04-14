-- Migration: CarviaCustoEntrega xerox de DespesaExtra (Nacom)
-- Idempotente: usa DO $$ ... $$ com information_schema checks.
--
-- 1. operacao_id DROP NOT NULL (permite fluxo compra)
-- 2. transportadora_id INTEGER NULL + FK + INDEX
-- 3. tipo_documento VARCHAR(20) NULL
-- 4. numero_documento VARCHAR(50) NULL
-- 5. Backfill tipo_documento/numero_documento para registros existentes

-- ---------- 1. operacao_id DROP NOT NULL ----------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_custos_entrega'
          AND column_name = 'operacao_id'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE carvia_custos_entrega
            ALTER COLUMN operacao_id DROP NOT NULL;
        RAISE NOTICE '[ok] operacao_id agora e nullable';
    ELSE
        RAISE NOTICE '[skip] operacao_id ja e nullable';
    END IF;
END $$;

-- ---------- 2. transportadora_id ----------
ALTER TABLE carvia_custos_entrega
    ADD COLUMN IF NOT EXISTS transportadora_id INTEGER NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'carvia_custos_entrega'
          AND constraint_name = 'fk_ce_transportadora'
    ) THEN
        ALTER TABLE carvia_custos_entrega
            ADD CONSTRAINT fk_ce_transportadora
            FOREIGN KEY (transportadora_id)
            REFERENCES transportadoras(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_carvia_custos_entrega_transportadora_id
    ON carvia_custos_entrega(transportadora_id);

-- ---------- 3-4. tipo_documento + numero_documento ----------
ALTER TABLE carvia_custos_entrega
    ADD COLUMN IF NOT EXISTS tipo_documento VARCHAR(20) NULL,
    ADD COLUMN IF NOT EXISTS numero_documento VARCHAR(50) NULL;

-- ---------- 5. Backfill ----------
UPDATE carvia_custos_entrega
   SET tipo_documento = 'CTE',
       numero_documento = COALESCE(numero_custo, 'PENDENTE_FATURA')
 WHERE tipo_documento IS NULL;
