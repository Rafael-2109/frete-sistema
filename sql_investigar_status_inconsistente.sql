-- =========================================
-- 🔍 INVESTIGAÇÃO DE STATUS INCONSISTENTE
-- =========================================
-- Script para investigar pedido VCD2563375 (ou outro pedido)
-- e entender por que alguns itens têm status diferente

-- 1️⃣ VERIFICAR TODOS OS ITENS DO PEDIDO
-- =========================================
SELECT
    num_pedido,
    cod_produto,
    status_pedido,
    qtd_produto_pedido,
    qtd_saldo_produto_pedido,
    expedicao,
    agendamento,
    data_pedido,
    data_atual_pedido
FROM carteira_principal
WHERE num_pedido = 'VCD2563863'  -- ⚠️ SUBSTITUA pelo pedido que você quer investigar
ORDER BY status_pedido, cod_produto;

-- 2️⃣ CONTAR ITENS POR STATUS
-- =========================================
SELECT
    num_pedido,
    status_pedido,
    COUNT(*) as qtd_itens,
    SUM(qtd_saldo_produto_pedido) as saldo_total
FROM carteira_principal
WHERE num_pedido = 'VCD2563863'  -- ⚠️ SUBSTITUA
GROUP BY num_pedido, status_pedido
ORDER BY status_pedido;

-- 3️⃣ VERIFICAR SE HÁ SEPARAÇÕES DESSES ITENS
-- =========================================
SELECT
    s.num_pedido,
    s.cod_produto,
    s.status as status_separacao,
    s.qtd_saldo as qtd_separada,
    s.sincronizado_nf,
    s.criado_em,
    cp.status_pedido as status_carteira
FROM separacao s
LEFT JOIN carteira_principal cp ON
    s.num_pedido = cp.num_pedido AND
    s.cod_produto = cp.cod_produto
WHERE s.num_pedido = 'VCD2563863'  -- ⚠️ SUBSTITUA
ORDER BY s.cod_produto;

-- 4️⃣ VERIFICAR SE HÁ FATURAMENTO DESSES ITENS
-- =========================================
SELECT
    f.origem as num_pedido,
    f.cod_produto,
    f.numero_nf,
    f.status_nf,
    f.qtd_produto_faturado,
    cp.status_pedido as status_carteira,
    cp.qtd_saldo_produto_pedido
FROM faturamento_produto f
LEFT JOIN carteira_principal cp ON
    f.origem = cp.num_pedido AND
    f.cod_produto = cp.cod_produto
WHERE f.origem = 'VCD2563375'  -- ⚠️ SUBSTITUA
ORDER BY f.cod_produto;

-- 5️⃣ HISTÓRICO: BUSCAR PEDIDOS COM STATUS INCONSISTENTE
-- =========================================
SELECT
    num_pedido,
    COUNT(DISTINCT status_pedido) as qtd_status_diferentes,
    STRING_AGG(DISTINCT status_pedido, ', ') as status_encontrados,
    COUNT(*) as total_itens
FROM carteira_principal
WHERE num_pedido LIKE 'V%'  -- Apenas pedidos Odoo
GROUP BY num_pedido
HAVING COUNT(DISTINCT status_pedido) > 1
ORDER BY num_pedido DESC
LIMIT 10;

-- 6️⃣ VERIFICAR CHAVE PRIMÁRIA (pedido + produto)
-- =========================================
-- Se houver duplicatas, pode ser esse o problema!
SELECT
    num_pedido,
    cod_produto,
    COUNT(*) as qtd_registros,
    STRING_AGG(DISTINCT status_pedido, ', ') as status_diferentes,
    STRING_AGG(CAST(id AS TEXT), ', ') as ids
FROM carteira_principal
WHERE num_pedido = 'VCD2563863'  -- ⚠️ SUBSTITUA
GROUP BY num_pedido, cod_produto
HAVING COUNT(*) > 1;

-- 7️⃣ DETALHES COMPLETOS DOS ITENS COM STATUS DIFERENTE
-- =========================================
WITH status_pedido AS (
    SELECT
        num_pedido,
        status_pedido,
        COUNT(*) as qtd
    FROM carteira_principal
    WHERE num_pedido = 'VCD2563863'  -- ⚠️ SUBSTITUA
    GROUP BY num_pedido, status_pedido
)
SELECT
    cp.id,
    cp.num_pedido,
    cp.cod_produto,
    cp.nome_produto,
    cp.status_pedido,
    sp.qtd as qtd_itens_com_esse_status,
    cp.qtd_produto_pedido,
    cp.qtd_saldo_produto_pedido,
    cp.qtd_cancelada_produto_pedido,
    cp.expedicao,
    cp.agendamento,
    cp.data_pedido,
    cp.observ_ped_1
FROM carteira_principal cp
JOIN status_pedido sp ON
    cp.num_pedido = sp.num_pedido AND
    cp.status_pedido = sp.status_pedido
WHERE cp.num_pedido = 'VCD2563375'  -- ⚠️ SUBSTITUA
ORDER BY cp.status_pedido, cp.cod_produto;

-- 8️⃣ VERIFICAR SE OS PRODUTOS SÃO DIFERENTES
-- =========================================
-- Talvez produtos "Cotação" sejam diferentes dos "Pedido de venda"?
SELECT
    status_pedido,
    cod_produto,
    nome_produto,
    qtd_saldo_produto_pedido
FROM carteira_principal
WHERE num_pedido = 'VCD2563863'  -- ⚠️ SUBSTITUA
ORDER BY status_pedido, cod_produto;

-- 9️⃣ CORREÇÃO: UPDATE para padronizar status
-- =========================================
-- ⚠️ NÃO EXECUTE AINDA! Apenas SQL de referência
-- Primeiro descubra qual é o status correto no Odoo!

/*
-- Opção 1: Forçar todos para "Pedido de venda"
UPDATE carteira_principal
SET status_pedido = 'Pedido de venda'
WHERE num_pedido = 'VCD2563375'
  AND status_pedido != 'Pedido de venda';

-- Opção 2: Forçar todos para "Cotação"
UPDATE carteira_principal
SET status_pedido = 'Cotação'
WHERE num_pedido = 'VCD2563375'
  AND status_pedido != 'Cotação';
*/

-- 🔟 ANÁLISE: Produtos que aparecem em múltiplas tabelas
-- =========================================
SELECT
    'CarteiraPrincipal' as fonte,
    num_pedido,
    cod_produto,
    status_pedido,
    qtd_saldo_produto_pedido as quantidade
FROM carteira_principal
WHERE num_pedido = 'VCD2563375'

UNION ALL

SELECT
    'Separacao' as fonte,
    num_pedido,
    cod_produto,
    status,
    qtd_saldo as quantidade
FROM separacao
WHERE num_pedido = 'VCD2563375'

UNION ALL

SELECT
    'FaturamentoProduto' as fonte,
    origem as num_pedido,
    cod_produto,
    status_nf,
    qtd_produto_faturado as quantidade
FROM faturamento_produto
WHERE origem = 'VCD2563375'

ORDER BY cod_produto, fonte;
