-- ============================================================================
-- SCRIPT SQL PARA RENDER: Adicionar campos de Entradas de Materiais
-- ============================================================================
--
-- OBJETIVO: Adicionar 4 campos em movimentacao_estoque para rastreabilidade
--           de entradas de materiais do Odoo (stock.picking + stock.move)
--
-- EXECUTAR NO: Shell do PostgreSQL do Render
--
-- Data: 2025-01-11
-- Autor: Sistema de Fretes
-- ============================================================================

-- 1️⃣ Adicionar campo odoo_picking_id (ID do recebimento no Odoo)
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS odoo_picking_id VARCHAR(50);

-- 2️⃣ Adicionar campo odoo_move_id (ID do movimento de estoque no Odoo)
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS odoo_move_id VARCHAR(50);

-- 3️⃣ Adicionar campo purchase_line_id (ID da linha de pedido de compra)
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS purchase_line_id VARCHAR(50);

-- 4️⃣ Adicionar campo pedido_compras_id (FK para pedido_compras local)
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS pedido_compras_id INTEGER;

-- 5️⃣ Criar índice em odoo_picking_id (busca rápida por recebimento)
CREATE INDEX IF NOT EXISTS idx_movimentacao_odoo_picking
ON movimentacao_estoque(odoo_picking_id);

-- 6️⃣ Criar índice em odoo_move_id (busca rápida por movimento e evitar duplicação)
CREATE INDEX IF NOT EXISTS idx_movimentacao_odoo_move
ON movimentacao_estoque(odoo_move_id);

-- 7️⃣ Criar FK para pedido_compras (opcional, apenas se tabela existir)
-- Se falhar, não tem problema - significa que a FK já existe ou a tabela não existe
ALTER TABLE movimentacao_estoque
ADD CONSTRAINT fk_movimentacao_pedido_compras
FOREIGN KEY (pedido_compras_id)
REFERENCES pedido_compras(id)
ON DELETE SET NULL;

-- ============================================================================
-- ✅ VERIFICAÇÃO: Execute para confirmar que campos foram criados
-- ============================================================================

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'movimentacao_estoque'
  AND column_name IN ('odoo_picking_id', 'odoo_move_id', 'purchase_line_id', 'pedido_compras_id')
ORDER BY column_name;

-- ============================================================================
-- 📊 VERIFICAÇÃO DE ÍNDICES
-- ============================================================================

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'movimentacao_estoque'
  AND indexname IN ('idx_movimentacao_odoo_picking', 'idx_movimentacao_odoo_move')
ORDER BY indexname;

-- ============================================================================
-- ✅ FIM DO SCRIPT
-- ============================================================================
--
-- RESULTADO ESPERADO:
-- - 4 campos adicionados em movimentacao_estoque
-- - 2 índices criados para performance
-- - 1 FK opcional (pode falhar se tabela não existir)
--
-- PRÓXIMOS PASSOS:
-- 1. Verificar se os campos foram criados (query acima)
-- 2. Reiniciar scheduler para iniciar importação de entradas
-- 3. Monitorar logs da importação
-- ============================================================================
