-- =============================================================================
-- MIGRACAO: Adicionar colunas de baixa adicional (desconto, acordo, devolucao)
-- =============================================================================
-- Rodar no Shell do Render: psql $DATABASE_URL -f add_baixa_colunas_adicionais.sql
-- Ou copiar e colar no psql interativo
-- =============================================================================

-- Campos de entrada do Excel
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS desconto_concedido_excel FLOAT DEFAULT 0;
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS acordo_comercial_excel FLOAT DEFAULT 0;
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS devolucao_excel FLOAT DEFAULT 0;

-- Campos de resultado do Odoo
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_desconto_odoo_id INTEGER;
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_desconto_odoo_name VARCHAR(100);
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_acordo_odoo_id INTEGER;
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_acordo_odoo_name VARCHAR(100);
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_devolucao_odoo_id INTEGER;
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_devolucao_odoo_name VARCHAR(100);

-- Verificar resultado
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'baixa_titulo_item'
  AND column_name IN (
    'desconto_concedido_excel', 'acordo_comercial_excel', 'devolucao_excel',
    'payment_desconto_odoo_id', 'payment_desconto_odoo_name',
    'payment_acordo_odoo_id', 'payment_acordo_odoo_name',
    'payment_devolucao_odoo_id', 'payment_devolucao_odoo_name'
  )
ORDER BY column_name;
