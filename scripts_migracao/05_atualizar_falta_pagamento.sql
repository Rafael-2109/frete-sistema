-- ============================================================================
-- Script SQL: Atualizar falta_pagamento em Separacoes existentes
-- Data: 23/10/2025
-- Ambiente: PostgreSQL (Render)
-- ============================================================================

-- OBJETIVO:
-- Marcar falta_pagamento=True para separações de pedidos com condição ANTECIPADO

BEGIN;

-- 1. Ver quantas separações serão afetadas (DRY RUN)
SELECT
    '========== PREVIEW: Separações que serão atualizadas ==========' as info;

SELECT
    COUNT(*) as total_separacoes,
    COUNT(DISTINCT separacao_lote_id) as total_lotes,
    COUNT(DISTINCT num_pedido) as total_pedidos
FROM separacao s
WHERE s.num_pedido IN (
    SELECT DISTINCT num_pedido
    FROM carteira_principal
    WHERE cond_pgto_pedido ILIKE '%ANTECIPADO%'
)
AND s.falta_pagamento = false
AND s.sincronizado_nf = false;

-- 2. Mostrar amostra de 10 registros
SELECT
    '========== AMOSTRA: Primeiros 10 registros ==========' as info;

SELECT
    s.id,
    s.separacao_lote_id,
    s.num_pedido,
    s.falta_pagamento as falta_pagamento_atual,
    cp.cond_pgto_pedido
FROM separacao s
INNER JOIN carteira_principal cp ON s.num_pedido = cp.num_pedido
WHERE cp.cond_pgto_pedido ILIKE '%ANTECIPADO%'
AND s.falta_pagamento = false
AND s.sincronizado_nf = false
LIMIT 10;

-- ============================================================================
-- ⚠️  PAUSA AQUI - REVISE OS RESULTADOS ACIMA
-- ============================================================================
-- Se estiver tudo correto, descomente as linhas abaixo para executar UPDATE:

/*
-- 3. EXECUTAR ATUALIZAÇÃO
UPDATE separacao
SET falta_pagamento = true
WHERE num_pedido IN (
    SELECT DISTINCT num_pedido
    FROM carteira_principal
    WHERE cond_pgto_pedido ILIKE '%ANTECIPADO%'
)
AND falta_pagamento = false
AND sincronizado_nf = false;

-- 4. Confirmar alterações
SELECT
    '========== RESULTADO: Atualização concluída ==========' as info;

SELECT
    COUNT(*) as total_separacoes_atualizadas,
    COUNT(DISTINCT separacao_lote_id) as lotes_afetados,
    COUNT(DISTINCT num_pedido) as pedidos_antecipados
FROM separacao
WHERE num_pedido IN (
    SELECT DISTINCT num_pedido
    FROM carteira_principal
    WHERE cond_pgto_pedido ILIKE '%ANTECIPADO%'
)
AND falta_pagamento = true
AND sincronizado_nf = false;

COMMIT;
*/

-- ⚠️  Por segurança, o script faz ROLLBACK por padrão
-- Descomente o bloco acima e comente a linha abaixo para executar
ROLLBACK;
