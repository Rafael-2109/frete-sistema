-- Migration: torna carvia_emissao_cte_complementar.custo_entrega_id NULLABLE.
-- Data: 2026-05-05
-- Idempotente: usa DO block que verifica is_nullable antes do ALTER.
-- Para Render Shell.

DO $$
DECLARE
    v_is_nullable text;
BEGIN
    SELECT is_nullable INTO v_is_nullable
    FROM information_schema.columns
    WHERE table_name = 'carvia_emissao_cte_complementar'
      AND column_name = 'custo_entrega_id'
      AND table_schema = 'public';

    IF v_is_nullable IS NULL THEN
        RAISE EXCEPTION 'Coluna carvia_emissao_cte_complementar.custo_entrega_id nao encontrada';
    END IF;

    IF v_is_nullable = 'NO' THEN
        ALTER TABLE carvia_emissao_cte_complementar
            ALTER COLUMN custo_entrega_id DROP NOT NULL;
        RAISE NOTICE 'ALTER aplicado: custo_entrega_id agora eh NULLABLE';
    ELSE
        RAISE NOTICE 'Coluna ja eh NULLABLE — nada a fazer';
    END IF;
END$$;

-- Verificacao final
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_name = 'carvia_emissao_cte_complementar'
  AND column_name = 'custo_entrega_id';
