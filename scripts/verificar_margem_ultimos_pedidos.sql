-- Script para verificar campos de margem, impostos e custo
-- dos últimos 10 num_pedido inseridos na CarteiraPrincipal
-- Data: 2025-12-30

-- Consulta principal: últimos 10 pedidos distintos com seus campos financeiros
SELECT DISTINCT ON (num_pedido)
    num_pedido,
    cod_produto,
    nome_produto,
    qtd_saldo_produto_pedido AS qtd_saldo,
    preco_produto_pedido AS preco_unit,

    -- Impostos
    icms_valor,
    icmsst_valor,
    pis_valor,
    cofins_valor,

    -- Custos
    custo_unitario_snapshot,
    custo_tipo_snapshot,
    custo_vigencia_snapshot,
    custo_producao_snapshot,
    custo_financeiro_pct_snapshot,
    custo_operacao_pct_snapshot,

    -- Margens
    margem_bruta,
    margem_bruta_percentual,
    margem_liquida,
    margem_liquida_percentual,

    created_at
FROM carteira_principal
ORDER BY num_pedido, created_at DESC
LIMIT 10;


-- Versão detalhada: todos os itens dos últimos 10 pedidos
SELECT
    num_pedido,
    cod_produto,
    nome_produto,
    qtd_saldo_produto_pedido AS qtd_saldo,
    preco_produto_pedido AS preco_unit,

    -- Impostos
    COALESCE(icms_valor, 0) AS icms,
    COALESCE(icmsst_valor, 0) AS icmsst,
    COALESCE(pis_valor, 0) AS pis,
    COALESCE(cofins_valor, 0) AS cofins,
    COALESCE(icms_valor, 0) + COALESCE(icmsst_valor, 0) +
        COALESCE(pis_valor, 0) + COALESCE(cofins_valor, 0) AS total_impostos,

    -- Custos
    custo_unitario_snapshot AS custo_unit,
    custo_tipo_snapshot AS tipo_custo,
    custo_producao_snapshot AS custo_prod,
    custo_financeiro_pct_snapshot AS fin_pct,
    custo_operacao_pct_snapshot AS oper_pct,

    -- Margens
    margem_bruta,
    margem_bruta_percentual AS mb_pct,
    margem_liquida,
    margem_liquida_percentual AS ml_pct,

    created_at
FROM carteira_principal
WHERE num_pedido IN (
    SELECT DISTINCT num_pedido
    FROM carteira_principal
    ORDER BY num_pedido DESC
    LIMIT 10
)
ORDER BY num_pedido DESC, cod_produto;


-- Resumo agregado por pedido
SELECT
    num_pedido,
    COUNT(*) AS qtd_itens,
    SUM(qtd_saldo_produto_pedido * preco_produto_pedido) AS valor_total,

    -- Impostos totais
    SUM(COALESCE(icms_valor, 0)) AS total_icms,
    SUM(COALESCE(icmsst_valor, 0)) AS total_icmsst,
    SUM(COALESCE(pis_valor, 0)) AS total_pis,
    SUM(COALESCE(cofins_valor, 0)) AS total_cofins,

    -- Margens agregadas
    SUM(margem_bruta) AS margem_bruta_total,
    ROUND(AVG(margem_bruta_percentual), 2) AS mb_pct_media,
    SUM(margem_liquida) AS margem_liquida_total,
    ROUND(AVG(margem_liquida_percentual), 2) AS ml_pct_media,

    -- Verificação de preenchimento
    COUNT(custo_unitario_snapshot) AS itens_com_custo,
    COUNT(margem_bruta) AS itens_com_margem,

    MAX(created_at) AS ultima_atualizacao
FROM carteira_principal
WHERE num_pedido IN (
    SELECT DISTINCT num_pedido
    FROM carteira_principal
    ORDER BY num_pedido DESC
    LIMIT 10
)
GROUP BY num_pedido
ORDER BY num_pedido DESC;
