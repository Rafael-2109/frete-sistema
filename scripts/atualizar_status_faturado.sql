-- Script SQL para atualizar status dos pedidos para FATURADO
-- quando a NF existe em FaturamentoProduto
-- 
-- Execute no psql do Render: 
-- psql $DATABASE_URL < scripts/atualizar_status_faturado.sql
--
-- Ou copie e cole no psql:
-- psql $DATABASE_URL

-- ============================================================
-- VERIFICAÇÃO PRÉVIA
-- ============================================================

-- Contar pedidos que serão afetados
SELECT COUNT(*) as "Total de pedidos que serão atualizados"
FROM pedidos p
INNER JOIN faturamento_produto fp ON p.nf = fp.numero_nf
WHERE p.nf IS NOT NULL 
AND p.nf != ''
AND p.status != 'FATURADO';

-- Mostrar amostra dos pedidos que serão atualizados (até 20)
SELECT 
    p.num_pedido as "Número Pedido", 
    p.nf as "Nota Fiscal", 
    p.status as "Status Atual", 
    'FATURADO' as "Novo Status"
FROM pedidos p
INNER JOIN faturamento_produto fp ON p.nf = fp.numero_nf
WHERE p.nf IS NOT NULL 
AND p.nf != ''
AND p.status != 'FATURADO'
ORDER BY p.num_pedido
LIMIT 20;

-- ============================================================
-- ATUALIZAÇÃO
-- ============================================================

-- ATUALIZAR STATUS PARA FATURADO
UPDATE pedidos 
SET status = 'FATURADO'
WHERE id IN (
    SELECT DISTINCT p.id
    FROM pedidos p
    INNER JOIN faturamento_produto fp ON p.nf = fp.numero_nf
    WHERE p.nf IS NOT NULL 
    AND p.nf != ''
    AND p.status != 'FATURADO'
);

-- ============================================================
-- VERIFICAÇÃO PÓS-ATUALIZAÇÃO
-- ============================================================

-- Resumo de status após atualização
SELECT 
    status as "Status", 
    COUNT(*) as "Total de Pedidos"
FROM pedidos
WHERE nf IS NOT NULL AND nf != ''
GROUP BY status
ORDER BY COUNT(*) DESC;

-- Verificar pedidos com NF mas sem registro em FaturamentoProduto (possível problema)
SELECT COUNT(*) as "Pedidos com NF sem registro de faturamento (verificar)"
FROM pedidos p
LEFT JOIN faturamento_produto fp ON p.nf = fp.numero_nf
WHERE p.nf IS NOT NULL 
AND p.nf != ''
AND fp.numero_nf IS NULL;

-- Listar alguns pedidos com problema (NF existe mas não está em faturamento)
SELECT 
    p.num_pedido as "Pedido",
    p.nf as "NF",
    p.status as "Status"
FROM pedidos p
LEFT JOIN faturamento_produto fp ON p.nf = fp.numero_nf
WHERE p.nf IS NOT NULL 
AND p.nf != ''
AND fp.numero_nf IS NULL
LIMIT 200;