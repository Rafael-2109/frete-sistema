-- ============================================================================
-- ANÁLISE DE RISCO: Vínculo DespesaExtra x FaturaFrete
-- Objetivo: Detectar casos de múltiplos matches e sem matches
-- Executar no Shell do Render
-- Data: 2025-01-23
-- ============================================================================

-- 1. ESTATÍSTICAS GERAIS
-- ============================================================================
SELECT
    'ESTATISTICAS GERAIS' as categoria,
    '' as detalhe,
    COUNT(*) as total
FROM despesas_extras
UNION ALL
SELECT
    'Despesas COM Fatura nas obs',
    '',
    COUNT(*)
FROM despesas_extras
WHERE observacoes ILIKE '%Fatura:%'
UNION ALL
SELECT
    'Despesas SEM Fatura nas obs',
    '',
    COUNT(*)
FROM despesas_extras
WHERE observacoes NOT ILIKE '%Fatura:%' OR observacoes IS NULL
UNION ALL
SELECT
    'Total de Faturas',
    '',
    COUNT(*)
FROM faturas_frete;

-- ============================================================================
-- 2. EXTRAÇÃO DO NÚMERO DA FATURA DAS OBSERVAÇÕES
-- Cria uma CTE para extrair o número da fatura de cada despesa
-- ============================================================================
WITH despesas_com_numero_fatura AS (
    SELECT
        de.id as despesa_id,
        de.frete_id,
        de.observacoes,
        -- Extrai o número da fatura: tudo entre "Fatura:" e o primeiro "|" ou fim da string
        TRIM(
            SPLIT_PART(
                SPLIT_PART(de.observacoes, 'Fatura:', 2),
                '|',
                1
            )
        ) as numero_fatura_extraido,
        f.transportadora_id
    FROM despesas_extras de
    LEFT JOIN fretes f ON de.frete_id = f.id
    WHERE de.observacoes ILIKE '%Fatura:%'
),

-- ============================================================================
-- 3. TENTA FAZER MATCH COM FATURAS USANDO "CONTAINS" (método atual problemático)
-- ============================================================================
matches_contains AS (
    SELECT
        dcnf.despesa_id,
        dcnf.numero_fatura_extraido,
        dcnf.transportadora_id,
        COUNT(ff.id) as qtd_matches_contains
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura LIKE '%' || dcnf.numero_fatura_extraido || '%'
    GROUP BY dcnf.despesa_id, dcnf.numero_fatura_extraido, dcnf.transportadora_id
),

-- ============================================================================
-- 4. TENTA FAZER MATCH EXATO (método correto)
-- ============================================================================
matches_exatos AS (
    SELECT
        dcnf.despesa_id,
        dcnf.numero_fatura_extraido,
        dcnf.transportadora_id,
        COUNT(ff.id) as qtd_matches_exatos,
        MAX(ff.id) as fatura_id  -- Pega o ID caso seja único
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
    GROUP BY dcnf.despesa_id, dcnf.numero_fatura_extraido, dcnf.transportadora_id
),

-- ============================================================================
-- 5. TENTA FAZER MATCH EXATO + TRANSPORTADORA (desempate)
-- ============================================================================
matches_com_transportadora AS (
    SELECT
        dcnf.despesa_id,
        dcnf.numero_fatura_extraido,
        dcnf.transportadora_id,
        COUNT(ff.id) as qtd_matches_transp,
        MAX(ff.id) as fatura_id  -- Pega o ID caso seja único
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
        AND ff.transportadora_id = dcnf.transportadora_id
    GROUP BY dcnf.despesa_id, dcnf.numero_fatura_extraido, dcnf.transportadora_id
)

-- ============================================================================
-- 6. ANÁLISE DE PROBLEMAS
-- ============================================================================
SELECT
    '========== RESUMO DE PROBLEMAS ==========' as info,
    '' as despesa_id,
    '' as numero_fatura,
    '' as status,
    0 as qtd_contains,
    0 as qtd_exatos,
    0 as qtd_transp
FROM (SELECT 1) dummy

UNION ALL

-- Total de cada tipo de caso
SELECT
    'TOTAIS',
    '',
    '',
    CASE
        WHEN mc.qtd_matches_contains > 1 THEN 'MULTIPLOS_MATCHES'
        WHEN me.qtd_matches_exatos = 0 THEN 'SEM_MATCH'
        WHEN me.qtd_matches_exatos = 1 THEN 'OK'
        ELSE 'OUTRO'
    END,
    COUNT(*),
    0,
    0
FROM matches_contains mc
JOIN matches_exatos me ON mc.despesa_id = me.despesa_id
GROUP BY
    CASE
        WHEN mc.qtd_matches_contains > 1 THEN 'MULTIPLOS_MATCHES'
        WHEN me.qtd_matches_exatos = 0 THEN 'SEM_MATCH'
        WHEN me.qtd_matches_exatos = 1 THEN 'OK'
        ELSE 'OUTRO'
    END

UNION ALL
SELECT '========================================', '', '', '', 0, 0, 0
FROM (SELECT 1) dummy

UNION ALL

-- ============================================================================
-- 7. CASOS PROBLEMÁTICOS DETALHADOS (primeiros 20)
-- ============================================================================
SELECT
    'CASO PROBLEMÁTICO',
    mc.despesa_id::text,
    mc.numero_fatura_extraido,
    CASE
        WHEN mc.qtd_matches_contains > 1 AND me.qtd_matches_exatos > 1 THEN 'MULT_MATCHES_EXATOS'
        WHEN mc.qtd_matches_contains > 1 AND me.qtd_matches_exatos = 1 THEN 'MULT_CONTAINS_OK_EXATO'
        WHEN mc.qtd_matches_contains > 1 AND me.qtd_matches_exatos = 0 THEN 'MULT_CONTAINS_SEM_EXATO'
        WHEN me.qtd_matches_exatos = 0 THEN 'SEM_MATCH'
        ELSE 'OUTRO'
    END,
    mc.qtd_matches_contains,
    me.qtd_matches_exatos,
    mct.qtd_matches_transp
FROM matches_contains mc
JOIN matches_exatos me ON mc.despesa_id = me.despesa_id
JOIN matches_com_transportadora mct ON mc.despesa_id = mct.despesa_id
WHERE
    mc.qtd_matches_contains > 1  -- Múltiplos matches com contains
    OR me.qtd_matches_exatos = 0  -- Sem match exato
ORDER BY
    mc.qtd_matches_contains DESC,
    me.qtd_matches_exatos DESC
LIMIT 20;


-- ============================================================================
-- 8. ANÁLISE DE NÚMEROS DE FATURA QUE SÃO SUBSTRING DE OUTROS
-- ============================================================================
SELECT
    '========== FATURAS QUE CAUSAM CONFLITO ==========' as categoria,
    '' as fatura_menor,
    '' as fatura_maior,
    0 as total
FROM (SELECT 1) dummy

UNION ALL

SELECT
    'SUBSTRING CONFLICT',
    ff1.numero_fatura,
    ff2.numero_fatura,
    1
FROM faturas_frete ff1
JOIN faturas_frete ff2
    ON ff1.numero_fatura != ff2.numero_fatura
    AND ff2.numero_fatura LIKE '%' || ff1.numero_fatura || '%'
ORDER BY LENGTH(ff1.numero_fatura)
LIMIT 10;


-- ============================================================================
-- 9. QUERY PARA VERIFICAR DESPESAS ESPECÍFICAS (ajuste o ID)
-- Descomente e ajuste o ID para investigar casos específicos
-- ============================================================================
/*
SELECT
    de.id as despesa_id,
    de.observacoes,
    TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1)) as numero_extraido,
    f.transportadora_id,
    (
        SELECT COUNT(*)
        FROM faturas_frete ff
        WHERE ff.numero_fatura LIKE '%' || TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1)) || '%'
    ) as matches_contains,
    (
        SELECT COUNT(*)
        FROM faturas_frete ff
        WHERE ff.numero_fatura = TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1))
    ) as matches_exatos,
    (
        SELECT COUNT(*)
        FROM faturas_frete ff
        WHERE ff.numero_fatura = TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1))
        AND ff.transportadora_id = f.transportadora_id
    ) as matches_com_transp
FROM despesas_extras de
LEFT JOIN fretes f ON de.frete_id = f.id
WHERE de.id = 123  -- AJUSTE O ID AQUI
AND de.observacoes ILIKE '%Fatura:%';
*/
