-- Migration: Aumentar precisao de colunas de quantidade de Numeric(15,3) para Numeric(18,6)
--
-- Motivacao:
--   Odoo usa 5 casas decimais para product_qty
--   DFe/NF-e XML usa ate 4 casas decimais (qCom)
--   Numeric(15,3) trunca a partir da 4a casa decimal
--   Numeric(18,6) cobre NF-e e Odoo sem perda
--
-- Operacao NAO-DESTRUTIVA: apenas adiciona zeros nas casas adicionais
--
-- Uso no Render Shell:
--   psql $DATABASE_URL -f scripts/migration_aumentar_precisao_quantidades.sql

BEGIN;

-- 1. Verificar estado atual
SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE (table_name, column_name) IN (
    ('match_nf_po_item', 'qtd_nf'),
    ('match_nf_po_item', 'qtd_po'),
    ('match_nf_po_alocacao', 'qtd_alocada'),
    ('recebimento_lf_lote', 'quantidade'),
    ('recebimento_lote', 'quantidade'),
    ('pedido_compras', 'qtd_produto_pedido'),
    ('pedido_compras', 'qtd_recebida'),
    ('historico_pedido_compras', 'qtd_produto_pedido'),
    ('historico_pedido_compras', 'qtd_recebida')
)
ORDER BY table_name, column_name;

-- 2. Executar alteracoes
ALTER TABLE match_nf_po_item ALTER COLUMN qtd_nf TYPE NUMERIC(18, 6);
ALTER TABLE match_nf_po_item ALTER COLUMN qtd_po TYPE NUMERIC(18, 6);
ALTER TABLE match_nf_po_alocacao ALTER COLUMN qtd_alocada TYPE NUMERIC(18, 6);
ALTER TABLE recebimento_lf_lote ALTER COLUMN quantidade TYPE NUMERIC(18, 6);
ALTER TABLE recebimento_lote ALTER COLUMN quantidade TYPE NUMERIC(18, 6);
ALTER TABLE pedido_compras ALTER COLUMN qtd_produto_pedido TYPE NUMERIC(18, 6);
ALTER TABLE pedido_compras ALTER COLUMN qtd_recebida TYPE NUMERIC(18, 6);
ALTER TABLE historico_pedido_compras ALTER COLUMN qtd_produto_pedido TYPE NUMERIC(18, 6);
ALTER TABLE historico_pedido_compras ALTER COLUMN qtd_recebida TYPE NUMERIC(18, 6);

-- 3. Verificar estado apos alteracao
SELECT table_name, column_name, numeric_precision, numeric_scale,
       CASE WHEN numeric_precision = 18 AND numeric_scale = 6 THEN 'OK' ELSE 'DIVERGENTE!' END AS status
FROM information_schema.columns
WHERE (table_name, column_name) IN (
    ('match_nf_po_item', 'qtd_nf'),
    ('match_nf_po_item', 'qtd_po'),
    ('match_nf_po_alocacao', 'qtd_alocada'),
    ('recebimento_lf_lote', 'quantidade'),
    ('recebimento_lote', 'quantidade'),
    ('pedido_compras', 'qtd_produto_pedido'),
    ('pedido_compras', 'qtd_recebida'),
    ('historico_pedido_compras', 'qtd_produto_pedido'),
    ('historico_pedido_compras', 'qtd_recebida')
)
ORDER BY table_name, column_name;

COMMIT;
