-- ================================================================================
-- 📊 COMPARAÇÃO DE PESOS - FATURAMENTO vs CADASTRO
-- Para executar no shell do PostgreSQL (Render ou Local)
-- ================================================================================

-- ================================================================================
-- QUERY 1: COMPARAR PESO UNITÁRIO
-- FaturamentoProduto.peso_unitario_produto vs CadastroPalletizacao.peso_bruto
-- ================================================================================

SELECT
    fp.numero_nf,
    fp.cod_produto,
    fp.nome_produto,
    fp.peso_unitario_produto as peso_unitario_faturamento,
    cp.peso_bruto as peso_bruto_cadastro,
    ROUND(
        (fp.peso_unitario_produto - cp.peso_bruto)::numeric,
        3
    ) as diferenca_peso,
    ROUND(
        (((fp.peso_unitario_produto - cp.peso_bruto) / NULLIF(cp.peso_bruto, 0)) * 100)::numeric,
        2
    ) as diferenca_percentual,
    COUNT(fp.id) as qtd_ocorrencias
FROM faturamento_produto fp
INNER JOIN cadastro_palletizacao cp
    ON fp.cod_produto = cp.cod_produto
WHERE fp.peso_unitario_produto != cp.peso_bruto  -- Apenas onde há diferença
GROUP BY
    fp.numero_nf,
    fp.cod_produto,
    fp.nome_produto,
    fp.peso_unitario_produto,
    cp.peso_bruto
ORDER BY
    ABS(fp.peso_unitario_produto - cp.peso_bruto) DESC  -- Maior diferença primeiro
LIMIT 100;


-- ================================================================================
-- QUERY 2: VALIDAR CÁLCULO DE PESO TOTAL
-- peso_total vs (qtd_produto_faturado * peso_unitario_produto)
-- ================================================================================

SELECT
    cod_produto,
    nome_produto,
    numero_nf,
    qtd_produto_faturado,
    peso_unitario_produto,
    peso_total as peso_total_registrado,
    ROUND(
        (qtd_produto_faturado * peso_unitario_produto)::numeric,
        3
    ) as peso_total_calculado,
    ROUND(
        (peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric,
        3
    ) as diferenca_peso,
    ROUND(
        (((peso_total - (qtd_produto_faturado * peso_unitario_produto)) / NULLIF(peso_total, 0)) * 100)::numeric,
        2
    ) as diferenca_percentual
FROM faturamento_produto
WHERE
    peso_total != (qtd_produto_faturado * peso_unitario_produto)  -- Apenas onde cálculo está errado
    AND peso_total > 0  -- Ignora peso zero
    AND qtd_produto_faturado > 0  -- Ignora quantidade zero
ORDER BY
    ABS(peso_total - (qtd_produto_faturado * peso_unitario_produto)) DESC  -- Maior diferença primeiro
LIMIT 100;


-- ================================================================================
-- QUERY 3 (BÔNUS): ESTATÍSTICAS GERAIS
-- Resumo das diferenças encontradas
-- ================================================================================

-- Resumo Query 1: Peso Unitário
SELECT
    '1. PESO UNITÁRIO' as tipo_analise,
    COUNT(DISTINCT fp.cod_produto) as total_produtos_diferentes,
    COUNT(*) as total_ocorrencias,
    ROUND(AVG(fp.peso_unitario_produto - cp.peso_bruto)::numeric, 3) as diferenca_media,
    ROUND(MIN(fp.peso_unitario_produto - cp.peso_bruto)::numeric, 3) as diferenca_minima,
    ROUND(MAX(fp.peso_unitario_produto - cp.peso_bruto)::numeric, 3) as diferenca_maxima
FROM faturamento_produto fp
INNER JOIN cadastro_palletizacao cp
    ON fp.cod_produto = cp.cod_produto
WHERE fp.peso_unitario_produto != cp.peso_bruto

UNION ALL

-- Resumo Query 2: Cálculo Peso Total
SELECT
    '2. PESO TOTAL CALCULADO' as tipo_analise,
    COUNT(DISTINCT cod_produto) as total_produtos_diferentes,
    COUNT(*) as total_ocorrencias,
    ROUND(AVG(peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3) as diferenca_media,
    ROUND(MIN(peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3) as diferenca_minima,
    ROUND(MAX(peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3) as diferenca_maxima
FROM faturamento_produto
WHERE
    peso_total != (qtd_produto_faturado * peso_unitario_produto)
    AND peso_total > 0
    AND qtd_produto_faturado > 0;


-- ================================================================================
-- QUERY 4 (BÔNUS): TOP 10 PRODUTOS COM MAIOR DIVERGÊNCIA
-- ================================================================================

SELECT
    fp.cod_produto,
    fp.nome_produto,
    COUNT(DISTINCT fp.numero_nf) as nfs_com_divergencia,
    ROUND(AVG(fp.peso_unitario_produto)::numeric, 3) as peso_unitario_medio_faturamento,
    cp.peso_bruto as peso_bruto_cadastro,
    ROUND((AVG(fp.peso_unitario_produto) - cp.peso_bruto)::numeric, 3) as diferenca_media,
    ROUND((((AVG(fp.peso_unitario_produto) - cp.peso_bruto) / NULLIF(cp.peso_bruto, 0)) * 100)::numeric, 2) as diferenca_percentual
FROM faturamento_produto fp
INNER JOIN cadastro_palletizacao cp
    ON fp.cod_produto = cp.cod_produto
WHERE fp.peso_unitario_produto != cp.peso_bruto
GROUP BY
    fp.cod_produto,
    fp.nome_produto,
    cp.peso_bruto
ORDER BY
    ABS(AVG(fp.peso_unitario_produto) - cp.peso_bruto) DESC
LIMIT 10;


-- ================================================================================
-- QUERY 5 (BÔNUS): VERIFICAR NFS ESPECÍFICAS COM ERRO DE CÁLCULO
-- Exemplo com NF específica (substitua '139906' pela NF desejada)
-- ================================================================================

SELECT
    numero_nf,
    cod_produto,
    nome_produto,
    qtd_produto_faturado,
    peso_unitario_produto,
    peso_total as peso_registrado,
    ROUND((qtd_produto_faturado * peso_unitario_produto)::numeric, 3) as peso_calculado,
    ROUND((peso_total - (qtd_produto_faturado * peso_unitario_produto))::numeric, 3) as diferenca,
    CASE
        WHEN peso_total = (qtd_produto_faturado * peso_unitario_produto) THEN '✅ CORRETO'
        WHEN ABS(peso_total - (qtd_produto_faturado * peso_unitario_produto)) < 0.1 THEN '⚠️  PEQUENA DIFERENÇA'
        ELSE '❌ ERRO'
    END as status
FROM faturamento_produto
WHERE numero_nf = '140059'
ORDER BY cod_produto;


-- ================================================================================
-- INSTRUÇÕES DE USO
-- ================================================================================

/*
📋 COMO USAR NO RENDER:

1. Acesse: https://dashboard.render.com
2. Selecione: seu banco PostgreSQL
3. Clique: "Connect" → "PSQL Command"
4. Cole o comando PSQL no terminal
5. Copie UMA das queries acima
6. Cole no shell PSQL
7. Pressione Enter
8. Veja os resultados!

💡 DICAS:

- Use QUERY 1 para ver diferenças entre peso unitário faturado vs cadastrado
- Use QUERY 2 para ver onde o cálculo de peso total está errado
- Use QUERY 3 para ter um resumo estatístico
- Use QUERY 4 para ver TOP 10 produtos com maior divergência
- Use QUERY 5 para verificar uma NF específica

⚠️ OBSERVAÇÃO:

Se aparecer erro "relation does not exist":
- Verifique se as tabelas existem: \dt faturamento_produto
- Verifique se as tabelas existem: \dt cadastro_palletizacao
*/
