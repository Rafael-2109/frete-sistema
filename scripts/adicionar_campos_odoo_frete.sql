-- ============================================================================
-- Script SQL: Adicionar Campos do Odoo na Tabela fretes
-- ============================================================================
-- OBJETIVO: Adicionar campos para vincular fretes com registros do Odoo
-- AUTOR: Sistema de Fretes
-- DATA: 14/11/2025
-- USO: Copiar e colar no Shell do Render (PostgreSQL)
-- ============================================================================

-- 1. Adicionar campos do Odoo
ALTER TABLE fretes ADD COLUMN IF NOT EXISTS odoo_dfe_id INTEGER;
ALTER TABLE fretes ADD COLUMN IF NOT EXISTS odoo_purchase_order_id INTEGER;
ALTER TABLE fretes ADD COLUMN IF NOT EXISTS odoo_invoice_id INTEGER;
ALTER TABLE fretes ADD COLUMN IF NOT EXISTS lancado_odoo_em TIMESTAMP;
ALTER TABLE fretes ADD COLUMN IF NOT EXISTS lancado_odoo_por VARCHAR(100);

-- 2. Criar índices
CREATE INDEX IF NOT EXISTS idx_fretes_odoo_dfe_id ON fretes(odoo_dfe_id);
CREATE INDEX IF NOT EXISTS idx_fretes_odoo_po_id ON fretes(odoo_purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_fretes_odoo_invoice_id ON fretes(odoo_invoice_id);

-- 3. Verificar criação
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'fretes'
AND column_name IN ('odoo_dfe_id', 'odoo_purchase_order_id', 'odoo_invoice_id',
                    'lancado_odoo_em', 'lancado_odoo_por')
ORDER BY column_name;

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
