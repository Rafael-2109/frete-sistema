-- =====================================================
-- VERIFICAÇÃO DE ENTRADAS DE MATERIAIS DO ODOO
-- =====================================================
-- Após a correção do scheduler, use este script para
-- verificar se as entradas estão sendo sincronizadas
-- =====================================================

-- 1️⃣ VERIFICAR ÚLTIMAS ENTRADAS SINCRONIZADAS
-- =====================================================
SELECT
    created_at as "Data Sincronização",
    cod_produto as "Código Produto",
    quantidade as "Quantidade",
    tipo as "Tipo",
    local as "Local",
    origem as "Origem",
    referencia as "Referência (Picking)",
    fornecedor_cnpj as "CNPJ Fornecedor"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
ORDER BY created_at DESC
LIMIT 20;

-- 2️⃣ ESTATÍSTICAS DAS ÚLTIMAS 24 HORAS
-- =====================================================
SELECT
    COUNT(*) as "Total Entradas",
    COUNT(DISTINCT cod_produto) as "Produtos Únicos",
    COUNT(DISTINCT fornecedor_cnpj) as "Fornecedores Únicos",
    SUM(quantidade) as "Quantidade Total",
    MIN(created_at) as "Primeira Entrada",
    MAX(created_at) as "Última Entrada"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
  AND created_at > NOW() - INTERVAL '24 hours';

-- 3️⃣ ENTRADAS POR DIA (ÚLTIMOS 7 DIAS)
-- =====================================================
SELECT
    DATE(created_at) as "Data",
    COUNT(*) as "Quantidade de Entradas",
    COUNT(DISTINCT cod_produto) as "Produtos Diferentes",
    SUM(quantidade) as "Quantidade Total"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY DATE(created_at) DESC;

-- 4️⃣ VERIFICAR SE FORNECEDORES DO GRUPO FORAM EXCLUÍDOS
-- =====================================================
-- Estes CNPJs NÃO devem aparecer (61.724.241 e 18.467.441)
SELECT
    fornecedor_cnpj as "CNPJ Fornecedor",
    COUNT(*) as "Quantidade de Entradas",
    CASE
        WHEN fornecedor_cnpj LIKE '61.724.241%' THEN '⚠️ FORNECEDOR DO GRUPO - NÃO DEVERIA APARECER'
        WHEN fornecedor_cnpj LIKE '18.467.441%' THEN '⚠️ FORNECEDOR DO GRUPO - NÃO DEVERIA APARECER'
        ELSE '✅ OK'
    END as "Status"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY fornecedor_cnpj
ORDER BY COUNT(*) DESC;

-- 5️⃣ PRODUTOS MAIS RECEBIDOS
-- =====================================================
SELECT
    cod_produto as "Código Produto",
    COUNT(*) as "Número de Entradas",
    SUM(quantidade) as "Quantidade Total",
    MAX(created_at) as "Última Entrada"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY cod_produto
ORDER BY SUM(quantidade) DESC
LIMIT 20;

-- 6️⃣ ENTRADAS COM VÍNCULO A PEDIDO DE COMPRA
-- =====================================================
SELECT
    me.created_at as "Data",
    me.cod_produto as "Produto",
    me.quantidade as "Qtd",
    me.referencia as "Picking",
    pc.numero as "Pedido Compra",
    pc.fornecedor_nome as "Fornecedor"
FROM movimentacao_estoque me
LEFT JOIN pedidos_compras pc ON me.pedido_compra_id = pc.id
WHERE me.tipo = 'ENTRADA'
  AND me.local = 'COMPRA'
  AND me.created_at > NOW() - INTERVAL '24 hours'
ORDER BY me.created_at DESC
LIMIT 20;

-- 7️⃣ ENTRADAS SEM VÍNCULO (pode indicar problema)
-- =====================================================
SELECT
    COUNT(*) as "Entradas Sem Pedido Compra",
    ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM movimentacao_estoque WHERE tipo = 'ENTRADA' AND local = 'COMPRA'), 0), 2) as "% do Total"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
  AND pedido_compra_id IS NULL
  AND created_at > NOW() - INTERVAL '7 days';

-- 8️⃣ COMPARAÇÃO ANTES/DEPOIS DA CORREÇÃO
-- =====================================================
-- Antes da correção: provavelmente 0 registros hoje
-- Depois da correção: deve ter registros recentes
SELECT
    DATE(created_at) as "Data",
    COUNT(*) as "Entradas Criadas",
    CASE
        WHEN DATE(created_at) = CURRENT_DATE THEN '✅ HOJE - Após correção'
        WHEN DATE(created_at) >= CURRENT_DATE - 1 THEN '⚠️ ONTEM'
        ELSE '❌ Mais antigo'
    END as "Status"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA'
  AND local = 'COMPRA'
  AND created_at > NOW() - INTERVAL '3 days'
GROUP BY DATE(created_at)
ORDER BY DATE(created_at) DESC;

-- 9️⃣ DIVERGÊNCIAS ENTRE PEDIDO COMPRA E ENTRADA
-- =====================================================
SELECT
    pc.numero as "Pedido Compra",
    pc.quantidade_total as "Qtd no Pedido",
    COALESCE(SUM(me.quantidade), 0) as "Qtd Recebida",
    pc.quantidade_total - COALESCE(SUM(me.quantidade), 0) as "Diferença",
    CASE
        WHEN COALESCE(SUM(me.quantidade), 0) = 0 THEN '⚠️ Nada recebido'
        WHEN pc.quantidade_total > COALESCE(SUM(me.quantidade), 0) THEN '⚠️ Recebimento parcial'
        WHEN pc.quantidade_total = COALESCE(SUM(me.quantidade), 0) THEN '✅ Recebimento completo'
        ELSE '⚠️ Recebido a mais'
    END as "Status"
FROM pedidos_compras pc
LEFT JOIN movimentacao_estoque me ON pc.id = me.pedido_compra_id AND me.tipo = 'ENTRADA' AND me.local = 'COMPRA'
WHERE pc.created_at > NOW() - INTERVAL '7 days'
  AND pc.estado != 'cancelled'
GROUP BY pc.id, pc.numero, pc.quantidade_total
ORDER BY pc.created_at DESC
LIMIT 20;

-- 🔟 RESUMO GERAL (DASHBOARD)
-- =====================================================
SELECT
    'Total Entradas (7 dias)' as "Métrica",
    COUNT(*)::text as "Valor"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA' AND local = 'COMPRA' AND created_at > NOW() - INTERVAL '7 days'

UNION ALL

SELECT
    'Entradas Hoje' as "Métrica",
    COUNT(*)::text as "Valor"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA' AND local = 'COMPRA' AND DATE(created_at) = CURRENT_DATE

UNION ALL

SELECT
    'Última Sincronização' as "Métrica",
    TO_CHAR(MAX(created_at), 'DD/MM/YYYY HH24:MI:SS') as "Valor"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA' AND local = 'COMPRA'

UNION ALL

SELECT
    'Produtos com Entrada (7 dias)' as "Métrica",
    COUNT(DISTINCT cod_produto)::text as "Valor"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA' AND local = 'COMPRA' AND created_at > NOW() - INTERVAL '7 days'

UNION ALL

SELECT
    'Fornecedores Ativos (7 dias)' as "Métrica",
    COUNT(DISTINCT fornecedor_cnpj)::text as "Valor"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA' AND local = 'COMPRA' AND created_at > NOW() - INTERVAL '7 days'

UNION ALL

SELECT
    'Entradas com Pedido Compra (%)' as "Métrica",
    ROUND(
        COUNT(CASE WHEN pedido_compra_id IS NOT NULL THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
        2
    )::text || '%' as "Valor"
FROM movimentacao_estoque
WHERE tipo = 'ENTRADA' AND local = 'COMPRA' AND created_at > NOW() - INTERVAL '7 days';

-- =====================================================
-- NOTAS:
-- =====================================================
-- ✅ Se as queries acima retornam dados recentes (hoje):
--    → Scheduler está funcionando corretamente
--
-- ⚠️ Se não há dados de hoje:
--    → Verificar log: cat logs/sincronizacao_incremental.log
--    → Verificar processo: ps aux | grep sincronizacao_incremental
--
-- ⚠️ Se aparecem CNPJs 61.724.241 ou 18.467.441:
--    → Filtro de fornecedores do grupo pode ter falhado
--
-- ✅ Sincronização normal:
--    → Entradas aparecem a cada 30 minutos
--    → Janela: últimos 7 dias do Odoo
--    → Apenas pickings com state='done' e type='incoming'
-- =====================================================
