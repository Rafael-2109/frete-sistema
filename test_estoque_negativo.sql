-- Teste SQL para verificar o estoque do produto 4310071
-- e entender por que está retornando valores zerados

-- 1. Verificar estoque atual
SELECT 
    cod_produto,
    SUM(CASE WHEN tipo_movimentacao = 'ENTRADA' THEN qtd_movimentacao ELSE -qtd_movimentacao END) as estoque_atual
FROM movimentacao_estoque
WHERE cod_produto = '4310071'
  AND (status_nf IS NULL OR status_nf != 'CANCELADO')
GROUP BY cod_produto;

-- 2. Verificar movimentações nos próximos dias
SELECT 
    cod_produto,
    tipo_movimentacao,
    data_movimentacao,
    qtd_movimentacao,
    status_nf
FROM movimentacao_estoque
WHERE cod_produto = '4310071'
  AND data_movimentacao >= CURRENT_DATE
  AND data_movimentacao <= CURRENT_DATE + INTERVAL '7 days'
ORDER BY data_movimentacao;

-- 3. Verificar separações pendentes
SELECT 
    cod_produto,
    expedicao,
    SUM(qtd_saldo) as total_pendente,
    COUNT(*) as num_pedidos
FROM separacao
WHERE cod_produto = '4310071'
  AND sincronizado_nf = false
  AND expedicao >= CURRENT_DATE
  AND expedicao <= CURRENT_DATE + INTERVAL '7 days'
GROUP BY cod_produto, expedicao
ORDER BY expedicao;

-- 4. Verificar produção programada
SELECT 
    cod_produto,
    data_movimentacao,
    qtd_movimentacao
FROM movimentacao_estoque
WHERE cod_produto = '4310071'
  AND tipo_movimentacao = 'ENTRADA'
  AND data_movimentacao >= CURRENT_DATE
  AND data_movimentacao <= CURRENT_DATE + INTERVAL '7 days'
ORDER BY data_movimentacao;