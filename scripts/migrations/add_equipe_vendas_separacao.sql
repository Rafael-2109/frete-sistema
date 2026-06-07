-- Migration: Adicionar coluna separacao.equipe_vendas + backfill
-- Data: 2026-06-07
-- Objetivo: Desnormalizar equipe_vendas (hoje obtido via LEFT JOIN caro com
--           carteira_principal na VIEW pedidos). Permite recriar a VIEW v8 SEM
--           o JOIN (710ms -> ~26-70ms por scan). equipe_vendas e constante por
--           num_pedido (validado: 0/8654 pedidos com divergencia entre produtos).
--
-- Idempotente (ADD COLUMN IF NOT EXISTS + UPDATE com IS DISTINCT FROM).
-- Executar no Render Shell ANTES de recriar a VIEW v8.

-- 1. Coluna (espelha tipo de carteira_principal.equipe_vendas = VARCHAR(100))
ALTER TABLE separacao ADD COLUMN IF NOT EXISTS equipe_vendas VARCHAR(100);

-- 2. Backfill: replica EXATAMENTE o que a VIEW v7 fazia
--    (LEFT JOIN ON num_pedido AND cod_produto, depois min() por lote).
--    Linhas sem match de produto ficam NULL — o min(s.equipe_vendas) por lote
--    na VIEW v8 pega o valor das linhas-irmas com match (resultado por lote
--    identico a v7).
UPDATE separacao s
SET equipe_vendas = cp.equipe_vendas
FROM carteira_principal cp
WHERE s.num_pedido = cp.num_pedido
  AND s.cod_produto = cp.cod_produto
  AND s.equipe_vendas IS DISTINCT FROM cp.equipe_vendas;
