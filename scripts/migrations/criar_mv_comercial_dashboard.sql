-- Migration: Materialized view para dashboard comercial
-- Elimina FULL OUTER JOIN pesado a cada render do dashboard
-- Refresh via scheduler (a cada 30 min)
-- Data: 2026-03-29

-- ============================================================
-- 1. View de equipes (dashboard principal)
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_comercial_equipes;

CREATE MATERIALIZED VIEW mv_comercial_equipes AS
WITH dados_carteira AS (
    SELECT
        equipe_vendas,
        COUNT(DISTINCT cnpj_cpf) as clientes_carteira,
        COALESCE(SUM(
            CASE
                WHEN qtd_saldo_produto_pedido > 0.02
                THEN ROUND((qtd_saldo_produto_pedido * preco_produto_pedido)::numeric, 2)
                ELSE 0
            END
        ), 0) as valor_carteira
    FROM carteira_principal
    WHERE equipe_vendas IS NOT NULL
    GROUP BY equipe_vendas
),
dados_faturamento AS (
    SELECT
        fp.equipe_vendas,
        COUNT(DISTINCT fp.cnpj_cliente) as clientes_faturamento,
        COALESCE(SUM(fp.valor_produto_faturado), 0) as valor_faturamento
    FROM faturamento_produto fp
    LEFT JOIN entregas_monitoradas em ON em.numero_nf = fp.numero_nf
    WHERE fp.equipe_vendas IS NOT NULL
      AND fp.status_nf != 'Cancelado'
      AND (em.status_finalizacao IS NULL OR em.status_finalizacao != 'Entregue')
    GROUP BY fp.equipe_vendas
)
SELECT
    COALESCE(dc.equipe_vendas, df.equipe_vendas) as equipe_vendas,
    COALESCE(dc.clientes_carteira, 0) + COALESCE(df.clientes_faturamento, 0) as total_clientes,
    COALESCE(dc.valor_carteira, 0) + COALESCE(df.valor_faturamento, 0) as valor_em_aberto,
    COALESCE(dc.clientes_carteira, 0) as clientes_carteira,
    COALESCE(dc.valor_carteira, 0) as valor_carteira,
    COALESCE(df.clientes_faturamento, 0) as clientes_faturamento,
    COALESCE(df.valor_faturamento, 0) as valor_faturamento
FROM dados_carteira dc
FULL OUTER JOIN dados_faturamento df ON dc.equipe_vendas = df.equipe_vendas;

-- Index para filtro por equipe
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_comercial_equipes_pk ON mv_comercial_equipes (equipe_vendas);

-- ============================================================
-- 2. View de vendedores (drill-down por equipe)
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_comercial_vendedores;

CREATE MATERIALIZED VIEW mv_comercial_vendedores AS
WITH vendedores_carteira AS (
    SELECT
        equipe_vendas,
        vendedor,
        COUNT(DISTINCT cnpj_cpf) as clientes_carteira,
        COALESCE(SUM(
            CASE
                WHEN qtd_saldo_produto_pedido > 0.02
                THEN ROUND((qtd_saldo_produto_pedido * preco_produto_pedido)::numeric, 2)
                ELSE 0
            END
        ), 0) as valor_carteira
    FROM carteira_principal
    WHERE equipe_vendas IS NOT NULL
      AND vendedor IS NOT NULL
    GROUP BY equipe_vendas, vendedor
),
vendedores_faturamento AS (
    SELECT
        fp.equipe_vendas,
        fp.vendedor,
        COUNT(DISTINCT fp.cnpj_cliente) as clientes_faturamento,
        COALESCE(SUM(fp.valor_produto_faturado), 0) as valor_faturamento
    FROM faturamento_produto fp
    LEFT JOIN entregas_monitoradas em ON em.numero_nf = fp.numero_nf
    WHERE fp.equipe_vendas IS NOT NULL
      AND fp.vendedor IS NOT NULL
      AND fp.status_nf != 'Cancelado'
      AND (em.status_finalizacao IS NULL OR em.status_finalizacao != 'Entregue')
    GROUP BY fp.equipe_vendas, fp.vendedor
)
SELECT
    COALESCE(vc.equipe_vendas, vf.equipe_vendas) as equipe_vendas,
    COALESCE(vc.vendedor, vf.vendedor) as vendedor,
    COALESCE(vc.clientes_carteira, 0) + COALESCE(vf.clientes_faturamento, 0) as total_clientes,
    COALESCE(vc.valor_carteira, 0) + COALESCE(vf.valor_faturamento, 0) as valor_em_aberto,
    COALESCE(vc.clientes_carteira, 0) as clientes_carteira,
    COALESCE(vc.valor_carteira, 0) as valor_carteira,
    COALESCE(vf.clientes_faturamento, 0) as clientes_faturamento,
    COALESCE(vf.valor_faturamento, 0) as valor_faturamento
FROM vendedores_carteira vc
FULL OUTER JOIN vendedores_faturamento vf
    ON vc.equipe_vendas = vf.equipe_vendas AND vc.vendedor = vf.vendedor;

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_comercial_vendedores_pk ON mv_comercial_vendedores (equipe_vendas, vendedor);
CREATE INDEX IF NOT EXISTS idx_mv_comercial_vendedores_equipe ON mv_comercial_vendedores (equipe_vendas);
