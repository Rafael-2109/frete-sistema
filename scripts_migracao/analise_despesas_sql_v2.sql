-- ============================================================================
-- ANÁLISE DE RISCO: Vínculo DespesaExtra x FaturaFrete
-- Objetivo: Detectar casos de múltiplos matches e sem matches
-- Executar no Shell do Render
-- Data: 2025-01-23
-- VERSÃO 2: Corrigida e dividida em queries independentes
-- ============================================================================

-- ============================================================================
-- QUERY 1: ESTATÍSTICAS GERAIS
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
-- QUERY 2: RESUMO DE PROBLEMAS
-- ============================================================================
WITH despesas_com_numero_fatura AS (
    SELECT
        de.id as despesa_id,
        de.frete_id,
        de.observacoes,
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
matches_exatos AS (
    SELECT
        dcnf.despesa_id,
        dcnf.numero_fatura_extraido,
        dcnf.transportadora_id,
        COUNT(ff.id) as qtd_matches_exatos,
        MAX(ff.id) as fatura_id
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
    GROUP BY dcnf.despesa_id, dcnf.numero_fatura_extraido, dcnf.transportadora_id
),
matches_com_transportadora AS (
    SELECT
        dcnf.despesa_id,
        dcnf.numero_fatura_extraido,
        dcnf.transportadora_id,
        COUNT(ff.id) as qtd_matches_transp,
        MAX(ff.id) as fatura_id
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
        AND ff.transportadora_id = dcnf.transportadora_id
    GROUP BY dcnf.despesa_id, dcnf.numero_fatura_extraido, dcnf.transportadora_id
)
SELECT
    CASE
        WHEN mc.qtd_matches_contains > 1 THEN 'MULTIPLOS_MATCHES_CONTAINS'
        WHEN me.qtd_matches_exatos = 0 THEN 'SEM_MATCH'
        WHEN me.qtd_matches_exatos = 1 THEN 'OK_MATCH_UNICO'
        WHEN me.qtd_matches_exatos > 1 THEN 'MULTIPLOS_MATCHES_EXATOS'
        ELSE 'OUTRO'
    END as status,
    COUNT(*) as quantidade,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM despesas_com_numero_fatura), 2) as percentual
FROM matches_contains mc
JOIN matches_exatos me ON mc.despesa_id = me.despesa_id
GROUP BY
    CASE
        WHEN mc.qtd_matches_contains > 1 THEN 'MULTIPLOS_MATCHES_CONTAINS'
        WHEN me.qtd_matches_exatos = 0 THEN 'SEM_MATCH'
        WHEN me.qtd_matches_exatos = 1 THEN 'OK_MATCH_UNICO'
        WHEN me.qtd_matches_exatos > 1 THEN 'MULTIPLOS_MATCHES_EXATOS'
        ELSE 'OUTRO'
    END
ORDER BY quantidade DESC;

-- ============================================================================
-- QUERY 3: CASOS PROBLEMÁTICOS DETALHADOS (primeiros 20)
-- ============================================================================
WITH despesas_com_numero_fatura AS (
    SELECT
        de.id as despesa_id,
        de.frete_id,
        de.observacoes,
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
matches_exatos AS (
    SELECT
        dcnf.despesa_id,
        dcnf.numero_fatura_extraido,
        dcnf.transportadora_id,
        COUNT(ff.id) as qtd_matches_exatos,
        MAX(ff.id) as fatura_id
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
    GROUP BY dcnf.despesa_id, dcnf.numero_fatura_extraido, dcnf.transportadora_id
),
matches_com_transportadora AS (
    SELECT
        dcnf.despesa_id,
        dcnf.numero_fatura_extraido,
        dcnf.transportadora_id,
        COUNT(ff.id) as qtd_matches_transp,
        MAX(ff.id) as fatura_id
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
        AND ff.transportadora_id = dcnf.transportadora_id
    GROUP BY dcnf.despesa_id, dcnf.numero_fatura_extraido, dcnf.transportadora_id
)
SELECT
    mc.despesa_id,
    mc.numero_fatura_extraido,
    mc.transportadora_id,
    CASE
        WHEN mc.qtd_matches_contains > 1 AND me.qtd_matches_exatos > 1 THEN 'MULT_MATCHES_EXATOS'
        WHEN mc.qtd_matches_contains > 1 AND me.qtd_matches_exatos = 1 THEN 'MULT_CONTAINS_OK_EXATO'
        WHEN mc.qtd_matches_contains > 1 AND me.qtd_matches_exatos = 0 THEN 'MULT_CONTAINS_SEM_EXATO'
        WHEN me.qtd_matches_exatos = 0 THEN 'SEM_MATCH'
        ELSE 'OUTRO'
    END as tipo_problema,
    mc.qtd_matches_contains,
    me.qtd_matches_exatos,
    mct.qtd_matches_transp
FROM matches_contains mc
JOIN matches_exatos me ON mc.despesa_id = me.despesa_id
JOIN matches_com_transportadora mct ON mc.despesa_id = mct.despesa_id
WHERE
    mc.qtd_matches_contains > 1
    OR me.qtd_matches_exatos = 0
    OR me.qtd_matches_exatos > 1
ORDER BY
    mc.qtd_matches_contains DESC,
    me.qtd_matches_exatos DESC
LIMIT 20;

-- ============================================================================
-- QUERY 4: FATURAS QUE SÃO SUBSTRING DE OUTRAS (Causam conflito no LIKE)
-- ============================================================================
SELECT
    ff1.numero_fatura as fatura_menor,
    ff2.numero_fatura as fatura_maior,
    ff1.transportadora_id as transp_menor,
    ff2.transportadora_id as transp_maior,
    CASE
        WHEN ff1.transportadora_id = ff2.transportadora_id THEN 'MESMA_TRANSP'
        ELSE 'TRANSP_DIFERENTE'
    END as situacao_transp
FROM faturas_frete ff1
JOIN faturas_frete ff2
    ON ff1.numero_fatura != ff2.numero_fatura
    AND ff2.numero_fatura LIKE '%' || ff1.numero_fatura || '%'
ORDER BY LENGTH(ff1.numero_fatura), ff1.numero_fatura
LIMIT 20;

-- ============================================================================
-- QUERY 5: EXEMPLOS REAIS DE NÚMEROS DE FATURA EXTRAÍDOS
-- Mostra como está sendo extraído o número das observações
-- ============================================================================
SELECT
    de.id as despesa_id,
    de.observacoes,
    TRIM(
        SPLIT_PART(
            SPLIT_PART(de.observacoes, 'Fatura:', 2),
            '|',
            1
        )
    ) as numero_extraido,
    LENGTH(TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1))) as tamanho
FROM despesas_extras de
WHERE de.observacoes ILIKE '%Fatura:%'
ORDER BY de.id DESC
LIMIT 10;

-- ============================================================================
-- QUERY 6: ESTATÍSTICAS DE RESOLUÇÃO COM TRANSPORTADORA
-- Verifica quantos casos de múltiplos matches podem ser resolvidos com transportadora
-- ============================================================================
WITH despesas_com_numero_fatura AS (
    SELECT
        de.id as despesa_id,
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
matches_exatos AS (
    SELECT
        dcnf.despesa_id,
        COUNT(ff.id) as qtd_matches_exatos
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
    GROUP BY dcnf.despesa_id
),
matches_com_transportadora AS (
    SELECT
        dcnf.despesa_id,
        COUNT(ff.id) as qtd_matches_transp
    FROM despesas_com_numero_fatura dcnf
    LEFT JOIN faturas_frete ff
        ON ff.numero_fatura = dcnf.numero_fatura_extraido
        AND ff.transportadora_id = dcnf.transportadora_id
    GROUP BY dcnf.despesa_id
)
SELECT
    'MULTIPLOS_RESOLVIDOS_COM_TRANSP' as categoria,
    COUNT(*) as quantidade
FROM matches_exatos me
JOIN matches_com_transportadora mct ON me.despesa_id = mct.despesa_id
WHERE me.qtd_matches_exatos > 1
AND mct.qtd_matches_transp = 1
UNION ALL
SELECT
    'MULTIPLOS_NAO_RESOLVIDOS_COM_TRANSP',
    COUNT(*)
FROM matches_exatos me
JOIN matches_com_transportadora mct ON me.despesa_id = mct.despesa_id
WHERE me.qtd_matches_exatos > 1
AND mct.qtd_matches_transp != 1;
