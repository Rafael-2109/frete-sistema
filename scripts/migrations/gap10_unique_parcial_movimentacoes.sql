-- GAP-10: Alterar UNIQUE(tipo_doc, doc_id) para partial unique index.
-- Exclui tipo_doc IN ('ajuste', 'saldo_inicial') para permitir multiplos ajustes.
-- Idempotente.

-- Remover constraint antiga (se existir)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_carvia_mov_tipo_doc'
    ) THEN
        ALTER TABLE carvia_conta_movimentacoes DROP CONSTRAINT uq_carvia_mov_tipo_doc;
        RAISE NOTICE 'Constraint uq_carvia_mov_tipo_doc removida.';
    END IF;
END $$;

-- Criar partial unique index (se nao existir)
CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_mov_tipo_doc_parcial
ON carvia_conta_movimentacoes (tipo_doc, doc_id)
WHERE tipo_doc NOT IN ('ajuste', 'saldo_inicial');
