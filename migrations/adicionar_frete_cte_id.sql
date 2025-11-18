-- Migration: Adicionar campo frete_cte_id em Frete
-- Data: 2025-01-18
-- Objetivo: Criar vínculo bidirecional entre Frete e ConhecimentoTransporte

-- Verificar se coluna já existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'fretes'
        AND column_name = 'frete_cte_id'
    ) THEN
        -- Adicionar coluna
        ALTER TABLE fretes
        ADD COLUMN frete_cte_id INTEGER REFERENCES conhecimento_transporte(id);

        -- Criar índice
        CREATE INDEX idx_frete_cte_id ON fretes(frete_cte_id);

        RAISE NOTICE 'Campo frete_cte_id adicionado com sucesso!';
    ELSE
        RAISE NOTICE 'Campo frete_cte_id já existe';
    END IF;
END $$;

-- Migrar vínculos existentes (onde ConhecimentoTransporte.frete_id já está preenchido)
UPDATE fretes f
SET frete_cte_id = ct.id
FROM conhecimento_transporte ct
WHERE ct.frete_id = f.id
AND f.frete_cte_id IS NULL;
