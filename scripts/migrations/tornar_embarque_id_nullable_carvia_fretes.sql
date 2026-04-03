-- Migration: CarviaFrete.embarque_id nullable
-- Permite criar CarviaFrete backfill sem embarque vinculado (historico pre-hook).
-- Idempotente: verifica constraint antes de alterar.
-- Tambem recria unique constraint como partial index (apenas WHERE embarque_id IS NOT NULL).

DO $$
BEGIN
    -- 1. Tornar embarque_id nullable
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_fretes'
        AND column_name = 'embarque_id'
        AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE carvia_fretes ALTER COLUMN embarque_id DROP NOT NULL;
        RAISE NOTICE 'carvia_fretes.embarque_id alterado para nullable';
    ELSE
        RAISE NOTICE 'carvia_fretes.embarque_id ja e nullable — nada a fazer';
    END IF;

    -- 2. Dropar unique constraint original (se existe)
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'carvia_fretes'
        AND constraint_name = 'uq_carvia_frete_embarque_cnpj'
    ) THEN
        ALTER TABLE carvia_fretes DROP CONSTRAINT uq_carvia_frete_embarque_cnpj;
        RAISE NOTICE 'Constraint uq_carvia_frete_embarque_cnpj removida';
    ELSE
        RAISE NOTICE 'Constraint uq_carvia_frete_embarque_cnpj nao existe — nada a dropar';
    END IF;
END $$;

-- 3. Recriar como partial unique index (apenas linhas com embarque_id NOT NULL)
-- Preserva semantica original para fretes com embarque, permite multiplos backfill (embarque_id NULL)
CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_frete_embarque_cnpj_notnull
    ON carvia_fretes (embarque_id, cnpj_emitente, cnpj_destino)
    WHERE embarque_id IS NOT NULL;
