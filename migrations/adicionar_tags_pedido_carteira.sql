-- ============================================================================
-- Script SQL: Adicionar campo tags_pedido em CarteiraPrincipal
-- ============================================================================
--
-- DESCRIÇÃO: Adiciona coluna tags_pedido (TEXT) para armazenar tags do Odoo
--            em formato JSON: [{"name": "VIP", "color": 5}]
--
-- USO NO RENDER SHELL:
--   1. Conectar ao banco: psql $DATABASE_URL
--   2. Copiar e colar este script
--   3. Verificar execução com: \d carteira_principal
--
-- Autor: Sistema de Fretes
-- Data: 2025-10-30
-- ============================================================================

-- Verificar se coluna já existe (retorna erro se não existir, ignorar erro)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'carteira_principal'
AND column_name = 'tags_pedido';

-- Adicionar coluna tags_pedido se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'carteira_principal'
        AND column_name = 'tags_pedido'
    ) THEN
        ALTER TABLE carteira_principal
        ADD COLUMN tags_pedido TEXT NULL;

        RAISE NOTICE '✅ Coluna tags_pedido adicionada com sucesso!';
    ELSE
        RAISE NOTICE '⚠️ Coluna tags_pedido já existe!';
    END IF;
END $$;

-- Verificar coluna criada
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'carteira_principal'
AND column_name = 'tags_pedido';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
