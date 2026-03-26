-- Migration: CarviaSubcontrato.operacao_id nullable
-- Permite criar CarviaSubcontrato independente de CarviaOperacao.
-- CarviaFrete e o eixo central; operacao e subcontrato sao filhos independentes.
-- Idempotente: verifica constraint antes de alterar.

DO $$
BEGIN
    -- Verificar se a coluna ainda e NOT NULL
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos'
        AND column_name = 'operacao_id'
        AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE carvia_subcontratos ALTER COLUMN operacao_id DROP NOT NULL;
        RAISE NOTICE 'carvia_subcontratos.operacao_id alterado para nullable';
    ELSE
        RAISE NOTICE 'carvia_subcontratos.operacao_id ja e nullable — nada a fazer';
    END IF;
END $$;
