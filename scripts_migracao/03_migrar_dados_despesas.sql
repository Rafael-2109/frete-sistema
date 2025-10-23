-- ============================================================================
-- SCRIPT 3: Migrar dados existentes - Vincular despesas às faturas
-- Objetivo: Preencher fatura_frete_id para as 829 despesas existentes
-- Executar: No Shell do Render (APÓS executar script 02)
-- Data: 2025-01-23
-- ============================================================================

-- IMPORTANTE: Este script é IDEMPOTENTE (pode ser executado várias vezes sem problemas)

-- ============================================================================
-- ETAPA 1: Migração de casos com MATCH ÚNICO (esperado: ~820 despesas)
-- ============================================================================
DO $$
DECLARE
    despesas_atualizadas INTEGER;
BEGIN
    -- Atualiza despesas que encontram exatamente 1 fatura
    WITH despesas_para_migrar AS (
        SELECT
            de.id as despesa_id,
            TRIM(
                SPLIT_PART(
                    SPLIT_PART(de.observacoes, 'Fatura:', 2),
                    '|',
                    1
                )
            ) as numero_fatura_extraido
        FROM despesas_extras de
        WHERE de.observacoes ILIKE '%Fatura:%'
        AND de.fatura_frete_id IS NULL  -- Só migra se ainda não foi migrado
    ),
    faturas_match_unico AS (
        SELECT
            dpm.despesa_id,
            ff.id as fatura_id
        FROM despesas_para_migrar dpm
        JOIN faturas_frete ff ON ff.numero_fatura = dpm.numero_fatura_extraido
        WHERE NOT EXISTS (
            -- Garante que só há 1 fatura com esse número
            SELECT 1
            FROM faturas_frete ff2
            WHERE ff2.numero_fatura = dpm.numero_fatura_extraido
            AND ff2.id != ff.id
        )
    )
    UPDATE despesas_extras de
    SET fatura_frete_id = fmu.fatura_id
    FROM faturas_match_unico fmu
    WHERE de.id = fmu.despesa_id;

    GET DIAGNOSTICS despesas_atualizadas = ROW_COUNT;
    RAISE NOTICE 'ETAPA 1: % despesas atualizadas com match único', despesas_atualizadas;
END $$;

-- ============================================================================
-- ETAPA 2: Migração de casos com MÚLTIPLOS MATCHES (esperado: ~10 despesas)
-- Estratégia: Escolher fatura com ID MENOR (mais antiga)
-- ============================================================================
DO $$
DECLARE
    despesas_atualizadas INTEGER;
BEGIN
    -- Atualiza despesas que encontram múltiplas faturas (escolhe a mais antiga)
    WITH despesas_para_migrar AS (
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
        AND de.fatura_frete_id IS NULL  -- Só migra se ainda não foi migrado
    ),
    faturas_multiplos_matches AS (
        SELECT
            dpm.despesa_id,
            MIN(ff.id) as fatura_id  -- Escolhe ID menor (mais antigo)
        FROM despesas_para_migrar dpm
        JOIN faturas_frete ff ON ff.numero_fatura = dpm.numero_fatura_extraido
        WHERE EXISTS (
            -- Garante que há múltiplas faturas com esse número
            SELECT 1
            FROM faturas_frete ff2
            WHERE ff2.numero_fatura = dpm.numero_fatura_extraido
            AND ff2.id != ff.id
        )
        GROUP BY dpm.despesa_id
    )
    UPDATE despesas_extras de
    SET fatura_frete_id = fmm.fatura_id
    FROM faturas_multiplos_matches fmm
    WHERE de.id = fmm.despesa_id;

    GET DIAGNOSTICS despesas_atualizadas = ROW_COUNT;
    RAISE NOTICE 'ETAPA 2: % despesas atualizadas com múltiplos matches', despesas_atualizadas;
END $$;

-- ============================================================================
-- RELATÓRIO FINAL DE MIGRAÇÃO
-- ============================================================================
SELECT
    '========== RESULTADO DA MIGRAÇÃO ==========' as info,
    COUNT(*) as total_despesas,
    SUM(CASE WHEN observacoes ILIKE '%Fatura:%' THEN 1 ELSE 0 END) as despesas_com_fatura_obs,
    SUM(CASE WHEN fatura_frete_id IS NOT NULL THEN 1 ELSE 0 END) as despesas_migradas,
    SUM(CASE WHEN observacoes ILIKE '%Fatura:%' AND fatura_frete_id IS NULL THEN 1 ELSE 0 END) as despesas_nao_migradas,
    ROUND(
        SUM(CASE WHEN fatura_frete_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN observacoes ILIKE '%Fatura:%' THEN 1 ELSE 0 END), 0),
        2
    ) as percentual_sucesso
FROM despesas_extras;

-- ============================================================================
-- DETALHAMENTO DAS DESPESAS NÃO MIGRADAS (se houver)
-- ============================================================================
SELECT
    '========== DESPESAS NÃO MIGRADAS ==========' as info,
    de.id as despesa_id,
    TRIM(
        SPLIT_PART(
            SPLIT_PART(de.observacoes, 'Fatura:', 2),
            '|',
            1
        )
    ) as numero_fatura_extraido,
    de.observacoes,
    (
        SELECT COUNT(*)
        FROM faturas_frete ff
        WHERE ff.numero_fatura = TRIM(SPLIT_PART(SPLIT_PART(de.observacoes, 'Fatura:', 2), '|', 1))
    ) as faturas_encontradas
FROM despesas_extras de
WHERE de.observacoes ILIKE '%Fatura:%'
AND de.fatura_frete_id IS NULL
ORDER BY de.id
LIMIT 20;

-- ============================================================================
-- VALIDAÇÃO: Comparar método antigo vs novo
-- ============================================================================
SELECT
    '========== VALIDAÇÃO MÉTODO ANTIGO VS NOVO ==========' as info,
    ff.id as fatura_id,
    ff.numero_fatura,
    -- Método ANTIGO (LIKE - problemático)
    (
        SELECT COUNT(*)
        FROM despesas_extras de
        WHERE de.observacoes LIKE '%' || ff.numero_fatura || '%'
    ) as despesas_metodo_antigo,
    -- Método NOVO (FK - correto)
    (
        SELECT COUNT(*)
        FROM despesas_extras de
        WHERE de.fatura_frete_id = ff.id
    ) as despesas_metodo_novo,
    -- Diferença
    (
        SELECT COUNT(*)
        FROM despesas_extras de
        WHERE de.observacoes LIKE '%' || ff.numero_fatura || '%'
    ) - (
        SELECT COUNT(*)
        FROM despesas_extras de
        WHERE de.fatura_frete_id = ff.id
    ) as diferenca
FROM faturas_frete ff
WHERE EXISTS (
    SELECT 1
    FROM despesas_extras de
    WHERE de.fatura_frete_id = ff.id
)
ORDER BY ABS(
    (SELECT COUNT(*) FROM despesas_extras de WHERE de.observacoes LIKE '%' || ff.numero_fatura || '%') -
    (SELECT COUNT(*) FROM despesas_extras de WHERE de.fatura_frete_id = ff.id)
) DESC
LIMIT 10;
