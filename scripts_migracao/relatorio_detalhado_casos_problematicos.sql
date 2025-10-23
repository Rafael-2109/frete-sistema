-- ============================================================================
-- RELATÓRIO DETALHADO: 9 Casos Problemáticos de Múltiplos Matches
-- Objetivo: Investigar profundamente os casos onde múltiplos matches exatos existem
-- Executar no Shell do Render
-- Data: 2025-01-23
-- ============================================================================

-- ============================================================================
-- PARTE 1: IDENTIFICAÇÃO DOS 9 CASOS PROBLEMÁTICOS
-- ============================================================================
WITH despesas_com_numero_fatura AS (
    SELECT
        de.id as despesa_id,
        de.frete_id,
        de.observacoes,
        de.valor_despesa,
        de.vencimento_despesa,
        de.tipo_despesa,
        de.setor_responsavel,
        de.criado_em,
        de.criado_por,
        TRIM(
            SPLIT_PART(
                SPLIT_PART(de.observacoes, 'Fatura:', 2),
                '|',
                1
            )
        ) as numero_fatura_extraido,
        f.transportadora_id,
        f.numero_cte,
        f.cnpj_cliente,
        f.nome_cliente
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
casos_problematicos AS (
    SELECT dcnf.*
    FROM despesas_com_numero_fatura dcnf
    JOIN matches_exatos me ON dcnf.despesa_id = me.despesa_id
    WHERE me.qtd_matches_exatos > 1
)
SELECT
    '========== IDENTIFICAÇÃO DOS 9 CASOS ==========' as separador,
    cp.despesa_id,
    cp.numero_fatura_extraido,
    cp.transportadora_id,
    cp.tipo_despesa,
    cp.valor_despesa,
    cp.vencimento_despesa,
    cp.criado_em,
    cp.criado_por
FROM casos_problematicos cp
ORDER BY cp.despesa_id;

-- ============================================================================
-- PARTE 2: DETALHAMENTO COMPLETO DE CADA CASO PROBLEMÁTICO
-- Mostra TODAS as faturas que fazem match com cada despesa
-- ============================================================================
WITH despesas_com_numero_fatura AS (
    SELECT
        de.id as despesa_id,
        de.frete_id,
        de.observacoes,
        de.valor_despesa,
        de.vencimento_despesa,
        de.tipo_despesa,
        TRIM(
            SPLIT_PART(
                SPLIT_PART(de.observacoes, 'Fatura:', 2),
                '|',
                1
            )
        ) as numero_fatura_extraido,
        f.transportadora_id,
        f.numero_cte,
        f.cnpj_cliente,
        f.nome_cliente,
        f.valor_cte
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
casos_problematicos AS (
    SELECT dcnf.*
    FROM despesas_com_numero_fatura dcnf
    JOIN matches_exatos me ON dcnf.despesa_id = me.despesa_id
    WHERE me.qtd_matches_exatos > 1
)
SELECT
    '========== DETALHAMENTO CASO A CASO ==========' as info,
    cp.despesa_id as desp_id,
    cp.numero_fatura_extraido as num_fat_extraido,
    cp.transportadora_id as transp_desp,
    cp.valor_despesa as vlr_desp,
    cp.vencimento_despesa as venc_desp,
    '--->' as seta,
    ff.id as fat_id,
    ff.numero_fatura as num_fat,
    ff.transportadora_id as transp_fat,
    ff.valor_total_fatura as vlr_fat,
    ff.vencimento as venc_fat,
    ff.data_emissao as emis_fat,
    t.razao_social as nome_transp,
    CASE
        WHEN cp.transportadora_id = ff.transportadora_id THEN 'MATCH_TRANSP'
        ELSE 'TRANSP_DIFERENTE'
    END as status_transp,
    CASE
        WHEN cp.vencimento_despesa = ff.vencimento THEN 'MATCH_VENC'
        ELSE 'VENC_DIFERENTE'
    END as status_venc
FROM casos_problematicos cp
JOIN faturas_frete ff ON ff.numero_fatura = cp.numero_fatura_extraido
LEFT JOIN transportadoras t ON ff.transportadora_id = t.id
ORDER BY cp.despesa_id, ff.id;

-- ============================================================================
-- PARTE 3: ANÁLISE DE DIFERENÇAS ENTRE AS FATURAS CANDIDATAS
-- Para cada caso, compara as faturas candidatas
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
        de.vencimento_despesa,
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
casos_problematicos AS (
    SELECT dcnf.*
    FROM despesas_com_numero_fatura dcnf
    JOIN matches_exatos me ON dcnf.despesa_id = me.despesa_id
    WHERE me.qtd_matches_exatos > 1
)
SELECT
    '========== ANÁLISE DE DIFERENÇAS ==========' as info,
    cp.despesa_id,
    cp.numero_fatura_extraido,
    COUNT(ff.id) as total_faturas_encontradas,
    COUNT(DISTINCT ff.transportadora_id) as qtd_transportadoras_diferentes,
    COUNT(DISTINCT ff.vencimento) as qtd_vencimentos_diferentes,
    COUNT(DISTINCT ff.data_emissao) as qtd_datas_emissao_diferentes,
    MIN(ff.data_emissao) as data_emissao_mais_antiga,
    MAX(ff.data_emissao) as data_emissao_mais_recente,
    SUM(CASE WHEN ff.transportadora_id = cp.transportadora_id THEN 1 ELSE 0 END) as faturas_mesma_transp,
    SUM(CASE WHEN ff.vencimento = cp.vencimento_despesa THEN 1 ELSE 0 END) as faturas_mesmo_venc
FROM casos_problematicos cp
JOIN faturas_frete ff ON ff.numero_fatura = cp.numero_fatura_extraido
GROUP BY cp.despesa_id, cp.numero_fatura_extraido
ORDER BY cp.despesa_id;

-- ============================================================================
-- PARTE 4: DADOS COMPLETOS DA DESPESA (para contexto)
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
        ) as numero_fatura_extraido
    FROM despesas_extras de
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
)
SELECT
    '========== DADOS COMPLETOS DAS DESPESAS ==========' as info,
    de.id,
    de.frete_id,
    de.tipo_despesa,
    de.setor_responsavel,
    de.motivo_despesa,
    de.tipo_documento,
    de.numero_documento,
    de.valor_despesa,
    de.vencimento_despesa,
    de.observacoes,
    de.criado_em,
    de.criado_por,
    f.numero_cte,
    f.cnpj_cliente,
    f.nome_cliente,
    f.transportadora_id,
    t.razao_social as transportadora_nome
FROM despesas_extras de
LEFT JOIN fretes f ON de.frete_id = f.id
LEFT JOIN transportadoras t ON f.transportadora_id = t.id
WHERE de.id IN (
    SELECT dcnf.despesa_id
    FROM despesas_com_numero_fatura dcnf
    JOIN matches_exatos me ON dcnf.despesa_id = me.despesa_id
    WHERE me.qtd_matches_exatos > 1
)
ORDER BY de.id;

-- ============================================================================
-- PARTE 5: RECOMENDAÇÃO DE VÍNCULO PARA CADA CASO
-- Aplica heurísticas para sugerir qual fatura vincular
-- ============================================================================
WITH despesas_com_numero_fatura AS (
    SELECT
        de.id as despesa_id,
        de.frete_id,
        de.vencimento_despesa,
        TRIM(
            SPLIT_PART(
                SPLIT_PART(de.observacoes, 'Fatura:', 2),
                '|',
                1
            )
        ) as numero_fatura_extraido,
        f.transportadora_id,
        f.data_emissao_cte
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
casos_problematicos AS (
    SELECT dcnf.*
    FROM despesas_com_numero_fatura dcnf
    JOIN matches_exatos me ON dcnf.despesa_id = me.despesa_id
    WHERE me.qtd_matches_exatos > 1
),
faturas_ranqueadas AS (
    SELECT
        cp.despesa_id,
        ff.id as fatura_id,
        ff.numero_fatura,
        ff.transportadora_id,
        ff.vencimento,
        ff.data_emissao,
        -- Pontuação para escolha automática
        (CASE WHEN ff.transportadora_id = cp.transportadora_id THEN 100 ELSE 0 END) +
        (CASE WHEN ff.vencimento = cp.vencimento_despesa THEN 50 ELSE 0 END) +
        (CASE WHEN ff.data_emissao = cp.data_emissao_cte THEN 25 ELSE 0 END) as pontuacao,
        ROW_NUMBER() OVER (
            PARTITION BY cp.despesa_id
            ORDER BY
                (CASE WHEN ff.transportadora_id = cp.transportadora_id THEN 0 ELSE 1 END),
                (CASE WHEN ff.vencimento = cp.vencimento_despesa THEN 0 ELSE 1 END),
                ff.data_emissao DESC
        ) as ranking
    FROM casos_problematicos cp
    JOIN faturas_frete ff ON ff.numero_fatura = cp.numero_fatura_extraido
)
SELECT
    '========== RECOMENDAÇÃO DE VÍNCULO ==========' as info,
    fr.despesa_id,
    fr.numero_fatura,
    fr.fatura_id as fatura_recomendada_id,
    fr.ranking,
    fr.pontuacao,
    CASE
        WHEN fr.pontuacao >= 100 THEN 'ALTA_CONFIANÇA'
        WHEN fr.pontuacao >= 50 THEN 'MÉDIA_CONFIANÇA'
        ELSE 'BAIXA_CONFIANÇA_MANUAL'
    END as nivel_confianca,
    fr.transportadora_id,
    fr.vencimento,
    fr.data_emissao
FROM faturas_ranqueadas fr
ORDER BY fr.despesa_id, fr.ranking;

-- ============================================================================
-- PARTE 6: RESUMO EXECUTIVO
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
        de.vencimento_despesa,
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
casos_problematicos AS (
    SELECT dcnf.*
    FROM despesas_com_numero_fatura dcnf
    JOIN matches_exatos me ON dcnf.despesa_id = me.despesa_id
    WHERE me.qtd_matches_exatos > 1
),
faturas_ranqueadas AS (
    SELECT
        cp.despesa_id,
        ff.id as fatura_id,
        (CASE WHEN ff.transportadora_id = cp.transportadora_id THEN 100 ELSE 0 END) +
        (CASE WHEN ff.vencimento = cp.vencimento_despesa THEN 50 ELSE 0 END) as pontuacao
    FROM casos_problematicos cp
    JOIN faturas_frete ff ON ff.numero_fatura = cp.numero_fatura_extraido
)
SELECT
    '========== RESUMO EXECUTIVO ==========' as categoria,
    COUNT(DISTINCT fr.despesa_id) as total_casos,
    SUM(CASE WHEN fr.pontuacao >= 100 THEN 1 ELSE 0 END) as casos_alta_confianca,
    SUM(CASE WHEN fr.pontuacao >= 50 AND fr.pontuacao < 100 THEN 1 ELSE 0 END) as casos_media_confianca,
    SUM(CASE WHEN fr.pontuacao < 50 THEN 1 ELSE 0 END) as casos_requerem_manual
FROM faturas_ranqueadas fr;
