-- Migration: Adicionar subcontrato_id em carvia_custos_entrega
-- Permite vincular CustoEntrega ao Subcontrato que cobra este custo
-- Executar via Render Shell (SQL idempotente)

ALTER TABLE carvia_custos_entrega ADD COLUMN IF NOT EXISTS subcontrato_id INTEGER;

-- FK com ON DELETE SET NULL (se sub for deletado, CE perde o vinculo)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_custo_entrega_subcontrato'
        AND table_name = 'carvia_custos_entrega'
    ) THEN
        ALTER TABLE carvia_custos_entrega
            ADD CONSTRAINT fk_custo_entrega_subcontrato
            FOREIGN KEY (subcontrato_id) REFERENCES carvia_subcontratos(id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_carvia_custo_entrega_subcontrato_id
ON carvia_custos_entrega (subcontrato_id);
