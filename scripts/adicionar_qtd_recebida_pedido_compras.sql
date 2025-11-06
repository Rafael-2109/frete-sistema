-- Script SQL para adicionar campo qtd_recebida à tabela pedido_compras
-- Para rodar no Shell do Render

-- ================================================
-- 1. ADICIONAR COLUNA qtd_recebida
-- ================================================
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS qtd_recebida NUMERIC(15, 3) DEFAULT 0;

-- ================================================
-- 2. VERIFICAR SE FOI CRIADA
-- ================================================
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND column_name = 'qtd_recebida';

-- ================================================
-- 3. ESTATÍSTICAS
-- ================================================
SELECT
    COUNT(*) as total_pedidos,
    COUNT(CASE WHEN qtd_recebida > 0 THEN 1 END) as com_recebimento,
    COUNT(CASE WHEN qtd_recebida = 0 THEN 1 END) as sem_recebimento
FROM pedido_compras
WHERE importado_odoo = TRUE;

-- ================================================
-- RESULTADO ESPERADO:
-- ================================================
-- ✅ Coluna: qtd_recebida
-- ✅ Tipo: numeric(15,3)
-- ✅ Default: 0
