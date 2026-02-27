-- Migration: Adicionar campo odoo_product_uom_id na tabela produto_fornecedor_depara
-- ID da UoM no Odoo (uom.uom). Usado no sync para product.supplierinfo.product_uom
-- Idempotente: pode rodar multiplas vezes sem erro

ALTER TABLE produto_fornecedor_depara
ADD COLUMN IF NOT EXISTS odoo_product_uom_id INTEGER;

COMMENT ON COLUMN produto_fornecedor_depara.odoo_product_uom_id
IS 'ID da UoM no Odoo (uom.uom). Usado no sync para product.supplierinfo.product_uom';
