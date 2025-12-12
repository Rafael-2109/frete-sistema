-- =============================================================================
-- MIGRACAO: Campos para lancamento de juros recebidos
-- =============================================================================
-- Data: 2025-12-12
-- Tabela: baixa_titulo_item
--
-- Novos campos:
-- - juros_excel: valor de juros do Excel
-- - payment_juros_odoo_id: ID do pagamento de juros no Odoo
-- - payment_juros_odoo_name: nome do pagamento de juros
-- =============================================================================

-- Adicionar campo juros_excel
ALTER TABLE baixa_titulo_item
ADD COLUMN IF NOT EXISTS juros_excel FLOAT DEFAULT 0;

-- Adicionar campo payment_juros_odoo_id
ALTER TABLE baixa_titulo_item
ADD COLUMN IF NOT EXISTS payment_juros_odoo_id INTEGER;

-- Adicionar campo payment_juros_odoo_name
ALTER TABLE baixa_titulo_item
ADD COLUMN IF NOT EXISTS payment_juros_odoo_name VARCHAR(100);

-- Verificar resultado
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'baixa_titulo_item'
AND column_name IN ('juros_excel', 'payment_juros_odoo_id', 'payment_juros_odoo_name')
ORDER BY column_name;
