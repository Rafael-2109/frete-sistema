-- ============================================================================
-- TESTE DE VALIDAÇÃO: Carteira Não-Odoo após correção de baixa_produto_pedido
-- Data: 2025-01-15
-- ============================================================================

-- 1. Verificar estrutura da tabela carteira_copia
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'carteira_copia'
  AND column_name IN ('baixa_produto_pedido', 'qtd_saldo_produto_calculado', 'qtd_produto_pedido', 'qtd_cancelada_produto_pedido')
ORDER BY ordinal_position;

-- 2. Verificar alguns registros de exemplo
SELECT
    num_pedido,
    cod_produto,
    qtd_produto_pedido,
    qtd_cancelada_produto_pedido,
    baixa_produto_pedido,
    qtd_saldo_produto_calculado,
    CASE
        WHEN (qtd_produto_pedido - qtd_cancelada_produto_pedido - baixa_produto_pedido) = qtd_saldo_produto_calculado
        THEN '✅ CORRETO'
        ELSE '❌ INCONSISTENTE'
    END as validacao
FROM carteira_copia
WHERE ativo = true
LIMIT 10;

-- 3. Buscar pedidos com faturamento (para verificar baixa)
SELECT
    cc.num_pedido,
    cc.cod_produto,
    cc.qtd_produto_pedido,
    cc.baixa_produto_pedido as baixa_coluna,
    COALESCE(SUM(fp.qtd_produto_faturado), 0) as baixa_calculada_faturamento,
    CASE
        WHEN cc.baixa_produto_pedido = COALESCE(SUM(fp.qtd_produto_faturado), 0)
        THEN '✅ CORRETO'
        ELSE '⚠️ DIFERENÇA'
    END as validacao_baixa
FROM carteira_copia cc
LEFT JOIN faturamento_produto fp ON fp.origem = cc.num_pedido AND fp.cod_produto = cc.cod_produto
WHERE cc.ativo = true
GROUP BY cc.num_pedido, cc.cod_produto, cc.qtd_produto_pedido, cc.baixa_produto_pedido
HAVING COALESCE(SUM(fp.qtd_produto_faturado), 0) > 0
LIMIT 10;

-- 4. Estatísticas gerais
SELECT
    COUNT(*) as total_registros,
    COUNT(CASE WHEN baixa_produto_pedido > 0 THEN 1 END) as com_baixa,
    COUNT(CASE WHEN qtd_saldo_produto_calculado > 0 THEN 1 END) as com_saldo,
    SUM(qtd_produto_pedido) as qtd_total_pedido,
    SUM(baixa_produto_pedido) as qtd_total_baixa,
    SUM(qtd_saldo_produto_calculado) as qtd_total_saldo
FROM carteira_copia
WHERE ativo = true;
