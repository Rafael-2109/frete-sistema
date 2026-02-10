-- Migration: Aumentar precisao de colunas de preco de Numeric(15,4) para Numeric(18,8)
--
-- Motivacao:
--   NF-e XML (vUnCom) suporta ate 10 casas decimais
--   Odoo usa float (~15 digitos) para price_unit
--   Numeric(15,4) trunca a partir da 5a casa decimal
--   Numeric(18,8) cobre NF-e e Odoo sem perda
--
-- Operacao NAO-DESTRUTIVA: apenas adiciona zeros nas casas adicionais
--
-- Uso no Render Shell:
--   psql $DATABASE_URL -f scripts/migration_aumentar_precisao_precos.sql

BEGIN;

-- 1. Verificar estado atual
SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE (table_name, column_name) IN (
    ('match_nf_po_item', 'preco_nf'),
    ('match_nf_po_item', 'preco_po'),
    ('match_nf_po_alocacao', 'preco_po'),
    ('pedido_compras', 'preco_produto_pedido'),
    ('historico_pedido_compras', 'preco_produto_pedido')
)
ORDER BY table_name, column_name;

-- 2. Executar alteracoes
ALTER TABLE match_nf_po_item ALTER COLUMN preco_nf TYPE NUMERIC(18, 8);
ALTER TABLE match_nf_po_item ALTER COLUMN preco_po TYPE NUMERIC(18, 8);
ALTER TABLE match_nf_po_alocacao ALTER COLUMN preco_po TYPE NUMERIC(18, 8);
ALTER TABLE pedido_compras ALTER COLUMN preco_produto_pedido TYPE NUMERIC(18, 8);
ALTER TABLE historico_pedido_compras ALTER COLUMN preco_produto_pedido TYPE NUMERIC(18, 8);

-- 3. Verificar estado apos alteracao
SELECT table_name, column_name, numeric_precision, numeric_scale,
       CASE WHEN numeric_precision = 18 AND numeric_scale = 8 THEN 'OK' ELSE 'DIVERGENTE!' END AS status
FROM information_schema.columns
WHERE (table_name, column_name) IN (
    ('match_nf_po_item', 'preco_nf'),
    ('match_nf_po_item', 'preco_po'),
    ('match_nf_po_alocacao', 'preco_po'),
    ('pedido_compras', 'preco_produto_pedido'),
    ('historico_pedido_compras', 'preco_produto_pedido')
)
ORDER BY table_name, column_name;

COMMIT;
