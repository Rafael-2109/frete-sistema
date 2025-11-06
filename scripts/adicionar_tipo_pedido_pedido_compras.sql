-- ============================================================
-- Script SQL: Adicionar campo tipo_pedido em pedido_compras
-- ============================================================
-- Executar no Shell do Render ou diretamente no PostgreSQL
-- ============================================================

-- 1. Verificar se coluna já existe
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND column_name = 'tipo_pedido';

-- 2. Adicionar coluna tipo_pedido
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS tipo_pedido VARCHAR(50);

-- 3. Criar índice
CREATE INDEX IF NOT EXISTS ix_pedido_compras_tipo_pedido
ON pedido_compras(tipo_pedido);

-- 4. Verificar estrutura final
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND column_name = 'tipo_pedido';

-- 5. Verificar índice criado
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'pedido_compras'
AND indexname = 'ix_pedido_compras_tipo_pedido';
