-- =====================================================================
-- Data fix idempotente — Corrige valor_mercadoria inflado em CarviaCotacao
-- + status ABERTO em CarviaPedido com NF ativa.
-- =====================================================================
-- Data: 2026-05-27
-- Documentacao: ver Python equivalente em
--   scripts/migrations/2026-05-27_backfill_carvia_cotacao_valor_mercadoria.py
--
-- Bug:
--   1. _agregar_totais_nfs_cotacao + api_anexar_nf_cotacao somavam
--      CarviaNf.valor_total (INFLADO com impostos) em vez de
--      CarviaPedidoItem.valor_total (mercadoria).
--   2. Wizard POST /carvia/cotacoes e api_anexar_nf_pedido nao chamavam
--      hook atualizar_status_pedido_carvia_pelo_faturamento.
--
-- Idempotente: WHERE filtra registros com inconsistencia. Reexecucao SAFE.
-- =====================================================================

\timing on

-- =====================================================================
-- PARTE A: Recalcular valor_mercadoria das cotacoes inflados
-- =====================================================================
BEGIN;

WITH soma_real AS (
    SELECT
        p.cotacao_id,
        SUM(pi.valor_total) AS soma_itens
    FROM carvia_pedidos p
    JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
    WHERE p.status != 'CANCELADO'
      AND pi.numero_nf IS NOT NULL
      AND pi.numero_nf != ''
    GROUP BY p.cotacao_id
),
to_update AS (
    SELECT
        c.id,
        c.numero_cotacao,
        c.valor_mercadoria AS valor_atual,
        sr.soma_itens AS valor_real
    FROM carvia_cotacoes c
    JOIN soma_real sr ON sr.cotacao_id = c.id
    WHERE c.valor_mercadoria > sr.soma_itens + 0.01
      AND c.status NOT IN ('CANCELADO', 'CANCELADA')
)
UPDATE carvia_cotacoes c
SET valor_mercadoria = tu.valor_real
FROM to_update tu
WHERE c.id = tu.id;

SELECT 'PARTE A: ' || COUNT(*) || ' cotacoes recalculadas'
FROM carvia_cotacoes c
JOIN (
    SELECT p.cotacao_id, SUM(pi.valor_total) AS soma_itens
    FROM carvia_pedidos p
    JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
    WHERE p.status != 'CANCELADO'
      AND pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
    GROUP BY p.cotacao_id
) sr ON sr.cotacao_id = c.id
WHERE ABS(c.valor_mercadoria - sr.soma_itens) < 0.01
  AND c.status NOT IN ('CANCELADO', 'CANCELADA');

COMMIT;

-- =====================================================================
-- PARTE B: Atualizar status ABERTO -> FATURADO quando todos itens
--          tem NF preenchida e ao menos uma NF esta ATIVA.
-- =====================================================================
BEGIN;

UPDATE carvia_pedidos p
SET status = 'FATURADO', atualizado_em = NOW()
WHERE p.status = 'ABERTO'
  AND EXISTS (
      -- Todos itens tem NF preenchida E ao menos uma NF ATIVA
      SELECT 1
      FROM carvia_pedido_itens pi
      JOIN carvia_nfs cn ON cn.numero_nf = pi.numero_nf
      WHERE pi.pedido_id = p.id
        AND cn.status = 'ATIVA'
  )
  AND NOT EXISTS (
      -- Nenhum item sem NF (todos os itens tem NF)
      SELECT 1
      FROM carvia_pedido_itens pi2
      WHERE pi2.pedido_id = p.id
        AND (pi2.numero_nf IS NULL OR pi2.numero_nf = '')
  );

SELECT 'PARTE B: ' || COUNT(*) || ' pedidos status=FATURADO'
FROM carvia_pedidos
WHERE status = 'FATURADO';

COMMIT;

-- =====================================================================
-- Validacao pos-backfill (sem alteracao)
-- =====================================================================
-- Confirma que nenhuma cotacao tem valor_mercadoria > soma real
SELECT
    'COTACOES AINDA INFLADAS' AS check_name,
    COUNT(*) AS n
FROM carvia_cotacoes c
JOIN (
    SELECT p.cotacao_id, SUM(pi.valor_total) AS soma_itens
    FROM carvia_pedidos p
    JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
    WHERE p.status != 'CANCELADO'
      AND pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
    GROUP BY p.cotacao_id
) sr ON sr.cotacao_id = c.id
WHERE c.valor_mercadoria > sr.soma_itens + 0.01
  AND c.status NOT IN ('CANCELADO', 'CANCELADA');

-- Confirma que nenhum pedido ABERTO tem todos os itens com NF ATIVA
SELECT
    'PEDIDOS ABERTO RESTANTES' AS check_name,
    COUNT(*) AS n
FROM carvia_pedidos p
WHERE p.status = 'ABERTO'
  AND EXISTS (
      SELECT 1 FROM carvia_pedido_itens pi
      JOIN carvia_nfs cn ON cn.numero_nf = pi.numero_nf
      WHERE pi.pedido_id = p.id AND cn.status = 'ATIVA'
  )
  AND NOT EXISTS (
      SELECT 1 FROM carvia_pedido_itens pi2
      WHERE pi2.pedido_id = p.id
        AND (pi2.numero_nf IS NULL OR pi2.numero_nf = '')
  );
