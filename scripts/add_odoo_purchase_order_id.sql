-- =============================================================================
-- Migration SQL para Render Shell
-- Adicionar campo odoo_purchase_order_id nas tabelas pedido_compras e historico
-- =============================================================================
--
-- PROBLEMA:
-- O campo `odoo_id` armazena o ID da LINHA (purchase.order.line), mas em
-- vários locais do sistema ele é usado como se fosse o ID do HEADER (purchase.order).
--
-- SOLUCAO:
-- Adicionar novo campo `odoo_purchase_order_id` para armazenar o ID do header.
--
-- EXECUTAR NO SHELL DO RENDER (PostgreSQL):
-- psql -c "..." ou copiar/colar no shell do banco
-- =============================================================================

-- 1. Adicionar o novo campo em pedido_compras
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS odoo_purchase_order_id VARCHAR(50);

-- 2. Criar indice para o novo campo
CREATE INDEX IF NOT EXISTS idx_pedido_compras_odoo_po_id
ON pedido_compras (odoo_purchase_order_id);

-- 3. Adicionar comentario explicativo
COMMENT ON COLUMN pedido_compras.odoo_purchase_order_id IS
'ID do header purchase.order no Odoo. Diferente de odoo_id que e o ID da linha purchase.order.line';

-- 4. Adicionar o campo no historico tambem
ALTER TABLE historico_pedido_compras
ADD COLUMN IF NOT EXISTS odoo_purchase_order_id VARCHAR(50);

-- =============================================================================
-- VERIFICACAO (opcional)
-- =============================================================================
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'pedido_compras'
-- AND column_name IN ('odoo_id', 'odoo_purchase_order_id');
--
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'historico_pedido_compras'
-- AND column_name IN ('odoo_id', 'odoo_purchase_order_id');
