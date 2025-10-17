-- ============================================================================
-- Migration: Adicionar campo 'importante' na tabela carteira_principal
-- Data: 2025-01-17
-- Descrição: Adiciona campo boolean para marcar pedidos importantes
-- ============================================================================

-- Verificar se coluna já existe (comentar se usar diretamente no Render)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='carteira_principal'
        AND column_name='importante'
    ) THEN
        -- Adicionar coluna
        ALTER TABLE carteira_principal
        ADD COLUMN importante BOOLEAN NOT NULL DEFAULT FALSE;

        -- Criar índice
        CREATE INDEX idx_carteira_importante
        ON carteira_principal(importante);

        RAISE NOTICE 'Coluna importante adicionada com sucesso!';
    ELSE
        RAISE NOTICE 'Coluna importante já existe!';
    END IF;
END $$;

-- ============================================================================
-- Verificação final
-- ============================================================================
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name='carteira_principal'
AND column_name='importante';
