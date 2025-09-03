-- ========================================
-- VERIFICAÇÃO DE DADOS DE PRODUÇÃO HOJE
-- ========================================

-- 1. Verificar se existe a tabela programacao_producao
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'programacao_producao'
ORDER BY ordinal_position;

-- 2. Verificar produção programada para HOJE
SELECT 
    cod_produto,
    data_programacao,
    qtd_programada,
    ativo,
    created_at
FROM programacao_producao
WHERE data_programacao = CURRENT_DATE
  AND ativo = true
ORDER BY cod_produto
LIMIT 20;

-- 3. Verificar produção programada para os PRÓXIMOS 7 DIAS
SELECT 
    data_programacao,
    COUNT(DISTINCT cod_produto) as produtos_programados,
    SUM(qtd_programada) as total_programado
FROM programacao_producao
WHERE data_programacao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
  AND ativo = true
GROUP BY data_programacao
ORDER BY data_programacao;

-- 4. Verificar movimentações de ENTRADA tipo PRODUÇÃO para hoje
SELECT 
    cod_produto,
    tipo_movimentacao,
    data_movimentacao,
    qtd_movimentacao,
    observacao
FROM movimentacao_estoque
WHERE data_movimentacao = CURRENT_DATE
  AND tipo_movimentacao IN ('ENTRADA', 'PRODUÇÃO', 'EST INICIAL')
  AND (status_nf IS NULL OR status_nf != 'CANCELADO')
ORDER BY cod_produto
LIMIT 20;

-- 5. Verificar produtos específicos do workspace (exemplo: 4310071)
SELECT 
    'programacao_producao' as origem,
    cod_produto,
    data_programacao as data,
    qtd_programada as quantidade,
    'PROGRAMADO' as status
FROM programacao_producao
WHERE cod_produto IN ('4310071', '4080177', '4320162')
  AND data_programacao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
  AND ativo = true

UNION ALL

SELECT 
    'movimentacao_estoque' as origem,
    cod_produto,
    data_movimentacao as data,
    qtd_movimentacao as quantidade,
    tipo_movimentacao as status
FROM movimentacao_estoque
WHERE cod_produto IN ('4310071', '4080177', '4320162')
  AND data_movimentacao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
  AND tipo_movimentacao IN ('ENTRADA', 'PRODUÇÃO')
  AND (status_nf IS NULL OR status_nf != 'CANCELADO')

ORDER BY cod_produto, data;

-- 6. Verificar se há QUALQUER produção programada no sistema
SELECT 
    COUNT(*) as total_registros,
    MIN(data_programacao) as primeira_data,
    MAX(data_programacao) as ultima_data,
    COUNT(DISTINCT cod_produto) as produtos_distintos
FROM programacao_producao
WHERE ativo = true;

-- 7. Debug: Ver estrutura e exemplos de movimentacao_estoque
SELECT DISTINCT tipo_movimentacao, COUNT(*) as qtd
FROM movimentacao_estoque
GROUP BY tipo_movimentacao
ORDER BY qtd DESC;

-- 8. Debug: Ver se há entradas futuras de qualquer tipo
SELECT 
    tipo_movimentacao,
    data_movimentacao,
    COUNT(*) as qtd_movimentacoes,
    SUM(qtd_movimentacao) as total_quantidade
FROM movimentacao_estoque
WHERE data_movimentacao >= CURRENT_DATE
  AND tipo_movimentacao LIKE '%ENTRADA%' OR tipo_movimentacao LIKE '%PRODU%'
  AND (status_nf IS NULL OR status_nf != 'CANCELADO')
GROUP BY tipo_movimentacao, data_movimentacao
ORDER BY data_movimentacao, tipo_movimentacao
LIMIT 30;