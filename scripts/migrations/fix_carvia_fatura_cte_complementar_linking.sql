-- Fix: Vincular CTe Complementar COMP-001 (cte_numero=121) a fatura 89-2 (id=137)
-- Problema: item da fatura com cte_numero=121 ficou com operacao_id=NULL
-- porque o LinkingService so buscava CarviaOperacao, nao CarviaCteComplementar.
-- Idempotente: condicoes WHERE impedem dupla execucao.

BEGIN;

-- 1. Vincular item 184 (CTe 121) a operacao 138 (pai do COMP-001)
UPDATE carvia_fatura_cliente_itens
SET operacao_id = 138
WHERE id = 184
  AND operacao_id IS NULL;

-- 2. Vincular CTe Comp COMP-001 a fatura 137 + status FATURADO
UPDATE carvia_cte_complementares
SET fatura_cliente_id = 137,
    status = 'FATURADO'
WHERE id = 1
  AND fatura_cliente_id IS NULL;

-- 3. Recalcular valor_total da fatura (ops + comps)
UPDATE carvia_faturas_cliente
SET valor_total = (
    SELECT COALESCE(SUM(o.cte_valor), 0)
    FROM carvia_operacoes o
    WHERE o.fatura_cliente_id = 137
) + (
    SELECT COALESCE(SUM(c.cte_valor), 0)
    FROM carvia_cte_complementares c
    WHERE c.fatura_cliente_id = 137
)
WHERE id = 137;

-- Verificacao
SELECT 'fatura' AS tipo, id, numero_fatura, valor_total::text, status
FROM carvia_faturas_cliente WHERE id = 137
UNION ALL
SELECT 'item_184', id::text, cte_numero, operacao_id::text, ''
FROM carvia_fatura_cliente_itens WHERE id = 184
UNION ALL
SELECT 'cte_comp', id::text, numero_comp, fatura_cliente_id::text, status
FROM carvia_cte_complementares WHERE id = 1;

COMMIT;
