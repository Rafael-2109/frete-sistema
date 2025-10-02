-- =========================================
-- 🔍 VALIDAR SE PRODUTOS FORAM REMOVIDOS
-- =========================================

-- 1️⃣ Ver se há produtos "fantasma" (que não existem mais no Odoo)
-- =========================================
-- Se os 3 produtos com "Cotação" não existem mais no pedido do Odoo,
-- eles NÃO viriam na sincronização mais recente

SELECT
    'Produtos com COTAÇÃO (suspeitos de removidos)' as tipo,
    cod_produto,
    nome_produto,
    qtd_produto_pedido,
    qtd_saldo_produto_pedido,
    data_atual_pedido,
    status_pedido
FROM carteira_principal
WHERE num_pedido = 'VCD2563863'
  AND status_pedido = 'Cotação'

UNION ALL

SELECT
    'Produtos com PEDIDO DE VENDA (ativos)' as tipo,
    cod_produto,
    nome_produto,
    qtd_produto_pedido,
    qtd_saldo_produto_pedido,
    data_atual_pedido,
    status_pedido
FROM carteira_principal
WHERE num_pedido = 'VCD2563863'
  AND status_pedido = 'Pedido de venda'
ORDER BY tipo, cod_produto
LIMIT 10;

-- 2️⃣ Verificar se foram faturados (se sim, não foram removidos)
-- =========================================
SELECT
    'Faturamento' as fonte,
    cod_produto,
    numero_nf,
    qtd_produto_faturado,
    status_nf
FROM faturamento_produto
WHERE origem = 'VCD2563863'
  AND cod_produto IN ('4210176', '4230162', '4759099')  -- Os 3 com Cotação
ORDER BY cod_produto;

-- 3️⃣ Verificar se foram separados (se sim, não foram removidos)
-- =========================================
SELECT
    'Separacao' as fonte,
    cod_produto,
    qtd_saldo,
    status,
    sincronizado_nf,
    criado_em
FROM separacao
WHERE num_pedido = 'VCD2563863'
  AND cod_produto IN ('4210176', '4230162', '4759099')  -- Os 3 com Cotação
ORDER BY cod_produto;

-- 4️⃣ ANÁLISE: Se produtos foram removidos, o sistema deveria deletá-los?
-- =========================================
-- Resposta: DEPENDE da lógica do código!
-- Vamos verificar...
