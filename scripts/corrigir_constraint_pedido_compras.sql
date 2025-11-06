-- ============================================================
-- Script SQL: Corrigir Constraint PedidoCompras
-- ============================================================
-- Remove unique de num_pedido e adiciona constraint composta
-- Executar no Shell do Render ou diretamente no PostgreSQL
-- ============================================================

-- 1. Verificar constraints existentes
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'pedido_compras'
AND constraint_type IN ('UNIQUE', 'PRIMARY KEY');

-- 2. Dropar índice único de num_pedido (se existir)
DROP INDEX IF EXISTS ix_pedido_compras_num_pedido CASCADE;

-- 3. Criar índice normal (não-único) para num_pedido
CREATE INDEX IF NOT EXISTS ix_pedido_compras_num_pedido
ON pedido_compras(num_pedido);

-- 4. Adicionar constraint composta UNIQUE (num_pedido, cod_produto)
ALTER TABLE pedido_compras
ADD CONSTRAINT uq_pedido_compras_num_cod_produto
UNIQUE (num_pedido, cod_produto);

-- 5. Verificar estrutura final
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'pedido_compras'
AND constraint_type IN ('UNIQUE', 'PRIMARY KEY');

-- 6. Verificar índices
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'pedido_compras';
