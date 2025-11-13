-- ============================================================================
-- Migration: Adicionar campos de NF no pedido_compras
-- ============================================================================
-- OBJETIVO: Adicionar campos para armazenar informações das NFs de entrada
-- DATA: 13/11/2025
-- EXECUTAR NO: Shell do Render (psql)
-- ============================================================================

-- 1. Adicionar campos
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS dfe_id VARCHAR(50);
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS nf_pdf_path VARCHAR(500);
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS nf_xml_path VARCHAR(500);
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS nf_chave_acesso VARCHAR(44);
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS nf_numero VARCHAR(20);
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS nf_serie VARCHAR(10);
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS nf_data_emissao DATE;
ALTER TABLE pedido_compras ADD COLUMN IF NOT EXISTS nf_valor_total NUMERIC(15, 2);

-- 2. Criar índices
CREATE INDEX IF NOT EXISTS idx_pedido_dfe ON pedido_compras (dfe_id);
CREATE INDEX IF NOT EXISTS idx_pedido_chave_acesso ON pedido_compras (nf_chave_acesso);

-- 3. Verificar campos criados
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND (column_name LIKE 'nf_%' OR column_name = 'dfe_id')
ORDER BY column_name;
