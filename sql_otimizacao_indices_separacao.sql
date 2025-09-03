-- =====================================================
-- OTIMIZAÇÃO DE ÍNDICES PARA TABELA SEPARACAO
-- Data: 2025-01-29
-- 
-- Adiciona índice composto otimizado para queries 
-- que filtram por pedido + produto + sincronização
-- =====================================================

-- 1. ÍNDICE COMPOSTO PARA WORKSPACE E CARTEIRA
-- Otimiza queries que buscam separações por pedido e produto
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_pedido_produto_sync 
ON separacao (num_pedido, cod_produto, sincronizado_nf)
WHERE sincronizado_nf = FALSE;  -- Índice parcial, só para não sincronizados

-- 2. ÍNDICE PARA AGREGAÇÃO POR PRODUTO
-- Otimiza GROUP BY cod_produto com filtro de sincronização
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_produto_qtd_sync
ON separacao (cod_produto, qtd_saldo)
WHERE sincronizado_nf = FALSE;

-- 3. ANALISAR ESTATÍSTICAS APÓS CRIAR ÍNDICES
ANALYZE separacao;

-- 4. VERIFICAR ÍNDICES CRIADOS
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'separacao'
AND indexname LIKE 'idx_sep%'
ORDER BY indexname;

-- 5. VERIFICAR USO DOS ÍNDICES (executar após queries)
-- EXPLAIN ANALYZE
-- SELECT 
--     cod_produto,
--     SUM(qtd_saldo) as qtd_total
-- FROM separacao
-- WHERE 
--     num_pedido = 'PEDIDO_TESTE'
--     AND sincronizado_nf = FALSE
-- GROUP BY cod_produto;