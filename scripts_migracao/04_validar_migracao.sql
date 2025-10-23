-- ============================================================================
-- SCRIPT 4: Validação completa da migração
-- Objetivo: Verificar se a migração foi bem-sucedida
-- Executar: No Shell do Render (APÓS executar script 03)
-- Data: 2025-01-23
-- ============================================================================

-- ============================================================================
-- VALIDAÇÃO 1: Estatísticas gerais
-- ============================================================================
SELECT
    '========== ESTATÍSTICAS GERAIS ==========' as categoria,
    COUNT(*) as total_despesas,
    SUM(CASE WHEN observacoes ILIKE '%Fatura:%' THEN 1 ELSE 0 END) as com_fatura_obs,
    SUM(CASE WHEN fatura_frete_id IS NOT NULL THEN 1 ELSE 0 END) as com_fk_preenchida,
    SUM(CASE WHEN observacoes ILIKE '%Fatura:%' AND fatura_frete_id IS NOT NULL THEN 1 ELSE 0 END) as migradas_sucesso,
    SUM(CASE WHEN observacoes ILIKE '%Fatura:%' AND fatura_frete_id IS NULL THEN 1 ELSE 0 END) as falha_migracao,
    ROUND(
        SUM(CASE WHEN observacoes ILIKE '%Fatura:%' AND fatura_frete_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN observacoes ILIKE '%Fatura:%' THEN 1 ELSE 0 END), 0),
        2
    ) as taxa_sucesso_pct
FROM despesas_extras;

-- ============================================================================
-- VALIDAÇÃO 2: Integridade referencial
-- Verifica se todas as FKs apontam para faturas válidas
-- ============================================================================
SELECT
    '========== INTEGRIDADE REFERENCIAL ==========' as categoria,
    COUNT(*) as despesas_com_fk,
    SUM(CASE WHEN ff.id IS NOT NULL THEN 1 ELSE 0 END) as fk_validas,
    SUM(CASE WHEN ff.id IS NULL THEN 1 ELSE 0 END) as fk_invalidas
FROM despesas_extras de
LEFT JOIN faturas_frete ff ON de.fatura_frete_id = ff.id
WHERE de.fatura_frete_id IS NOT NULL;

-- ============================================================================
-- VALIDAÇÃO 3: Comparação de totais por fatura (antigo vs novo)
-- ============================================================================
WITH comparacao AS (
    SELECT
        ff.id as fatura_id,
        ff.numero_fatura,
        -- Método antigo (LIKE)
        (
            SELECT COUNT(*)
            FROM despesas_extras de
            WHERE de.observacoes LIKE '%Fatura: ' || ff.numero_fatura || '%'
        ) as total_antigo,
        -- Método novo (FK)
        COUNT(de.id) as total_novo
    FROM faturas_frete ff
    LEFT JOIN despesas_extras de ON de.fatura_frete_id = ff.id
    GROUP BY ff.id, ff.numero_fatura
)
SELECT
    '========== COMPARAÇÃO ANTIGO VS NOVO ==========' as info,
    COUNT(*) as total_faturas,
    SUM(CASE WHEN total_antigo = total_novo THEN 1 ELSE 0 END) as faturas_ok,
    SUM(CASE WHEN total_antigo != total_novo THEN 1 ELSE 0 END) as faturas_divergentes,
    ROUND(
        SUM(CASE WHEN total_antigo = total_novo THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) as taxa_consistencia_pct
FROM comparacao
WHERE total_antigo > 0 OR total_novo > 0;

-- ============================================================================
-- VALIDAÇÃO 4: Casos divergentes (antigo vs novo)
-- ============================================================================
WITH comparacao AS (
    SELECT
        ff.id as fatura_id,
        ff.numero_fatura,
        (
            SELECT COUNT(*)
            FROM despesas_extras de
            WHERE de.observacoes LIKE '%Fatura: ' || ff.numero_fatura || '%'
        ) as total_antigo,
        COUNT(de.id) as total_novo
    FROM faturas_frete ff
    LEFT JOIN despesas_extras de ON de.fatura_frete_id = ff.id
    GROUP BY ff.id, ff.numero_fatura
)
SELECT
    '========== CASOS DIVERGENTES ==========' as info,
    fatura_id,
    numero_fatura,
    total_antigo,
    total_novo,
    (total_antigo - total_novo) as diferenca
FROM comparacao
WHERE total_antigo != total_novo
ORDER BY ABS(total_antigo - total_novo) DESC
LIMIT 10;

-- ============================================================================
-- VALIDAÇÃO 5: Exemplos de despesas migradas com sucesso
-- ============================================================================
SELECT
    '========== EXEMPLOS DE SUCESSO ==========' as info,
    de.id as despesa_id,
    de.observacoes,
    TRIM(
        SPLIT_PART(
            SPLIT_PART(de.observacoes, 'Fatura:', 2),
            '|',
            1
        )
    ) as numero_extraido,
    de.fatura_frete_id,
    ff.numero_fatura as fatura_vinculada,
    CASE
        WHEN TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1)) = ff.numero_fatura
        THEN 'MATCH_OK'
        ELSE 'DIVERGENTE'
    END as validacao
FROM despesas_extras de
JOIN faturas_frete ff ON de.fatura_frete_id = ff.id
WHERE de.observacoes ILIKE '%Fatura:%'
ORDER BY de.id DESC
LIMIT 10;

-- ============================================================================
-- VALIDAÇÃO 6: Despesas que falharam na migração (se houver)
-- ============================================================================
SELECT
    '========== FALHAS NA MIGRAÇÃO ==========' as info,
    de.id as despesa_id,
    de.observacoes,
    TRIM(
        SPLIT_PART(
            SPLIT_PART(de.observacoes, 'Fatura:', 2),
            '|',
            1
        )
    ) as numero_extraido,
    (
        SELECT COUNT(*)
        FROM faturas_frete ff
        WHERE ff.numero_fatura = TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1))
    ) as faturas_encontradas
FROM despesas_extras de
WHERE de.observacoes ILIKE '%Fatura:%'
AND de.fatura_frete_id IS NULL
LIMIT 10;

-- ============================================================================
-- VALIDAÇÃO 7: Resumo executivo
-- ============================================================================
WITH stats AS (
    SELECT
        COUNT(*) as total_despesas,
        SUM(CASE WHEN observacoes ILIKE '%Fatura:%' THEN 1 ELSE 0 END) as esperadas,
        SUM(CASE WHEN fatura_frete_id IS NOT NULL THEN 1 ELSE 0 END) as migradas
    FROM despesas_extras
)
SELECT
    '========== RESUMO EXECUTIVO ==========' as categoria,
    total_despesas,
    esperadas as despesas_com_fatura,
    migradas as despesas_migradas,
    (esperadas - migradas) as despesas_pendentes,
    ROUND(migradas * 100.0 / NULLIF(esperadas, 0), 2) as taxa_sucesso_pct,
    CASE
        WHEN migradas = esperadas THEN '✅ MIGRAÇÃO 100% COMPLETA'
        WHEN migradas >= esperadas * 0.99 THEN '✅ MIGRAÇÃO >99% (ACEITÁVEL)'
        WHEN migradas >= esperadas * 0.95 THEN '⚠️ MIGRAÇÃO >95% (REVISAR PENDENTES)'
        ELSE '❌ MIGRAÇÃO INCOMPLETA (INVESTIGAR)'
    END as status
FROM stats;
