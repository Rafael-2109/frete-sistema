-- =====================================================
-- Script: Remover campo crossdocking_id de ClienteMoto
-- Data: 2025-10-08
-- Motivo: Campo desnecessário - haverá apenas 1 CrossDocking genérico
-- =====================================================

-- 1. Remover constraint de FK
ALTER TABLE cliente_moto
DROP CONSTRAINT IF EXISTS cliente_moto_crossdocking_id_fkey;

-- 2. Remover índice
DROP INDEX IF EXISTS ix_cliente_moto_crossdocking_id;

-- 3. Remover coluna crossdocking_id
ALTER TABLE cliente_moto
DROP COLUMN IF EXISTS crossdocking_id;

-- 4. Verificar estrutura final (apenas para conferência)
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'cliente_moto'
ORDER BY ordinal_position;

-- ✅ RESULTADO ESPERADO:
-- - Coluna crossdocking_id REMOVIDA
-- - Coluna crossdocking (boolean) MANTIDA
-- - Coluna vendedor_id (FK) MANTIDA
