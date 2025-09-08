-- =====================================================
-- ANÁLISE COMPLETA DE ÍNDICES - SISTEMA FRETE
-- Data: 2025-09-06
-- Objetivo: Identificar índices redundantes, não utilizados e oportunidades de otimização
-- =====================================================

-- =====================================================
-- 1. VISÃO GERAL: TODOS OS ÍNDICES DO BANCO
-- =====================================================
\echo '========================================='
\echo '1. LISTAGEM COMPLETA DE ÍNDICES'
\echo '========================================='

SELECT 
    schemaname AS schema,
    tablename AS tabela,
    indexname AS indice,
    indexdef AS definicao,
    pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho,
    idx_scan AS num_scans,
    idx_tup_read AS tuplas_lidas,
    idx_tup_fetch AS tuplas_retornadas,
    CASE 
        WHEN idx_scan = 0 THEN 'NUNCA USADO'
        WHEN idx_scan < 10 THEN 'POUCO USADO'
        WHEN idx_scan < 100 THEN 'USO MODERADO'
        ELSE 'MUITO USADO'
    END AS categoria_uso
FROM pg_stat_user_indexes
JOIN pg_indexes ON pg_indexes.indexname = pg_stat_user_indexes.indexrelname
WHERE schemaname = 'public'
ORDER BY 
    idx_scan ASC,
    pg_relation_size(indexrelid) DESC;

-- =====================================================
-- 2. ÍNDICES NUNCA UTILIZADOS (CANDIDATOS A REMOÇÃO)
-- =====================================================
\echo ''
\echo '========================================='
\echo '2. ÍNDICES NUNCA UTILIZADOS'
\echo '========================================='

SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho_desperdicado,
    'DROP INDEX IF EXISTS ' || indexname || ';' AS comando_remocao
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND idx_scan = 0
    AND indexrelname NOT LIKE '%_pkey'  -- Não remove chaves primárias
    AND indexrelname NOT LIKE '%_unique' -- Cuidado com unique constraints
ORDER BY pg_relation_size(indexrelid) DESC;

-- =====================================================
-- 3. ÍNDICES DUPLICADOS E REDUNDANTES
-- =====================================================
\echo ''
\echo '========================================='
\echo '3. ÍNDICES DUPLICADOS/REDUNDANTES'
\echo '========================================='

WITH index_columns AS (
    SELECT 
        n.nspname AS schema_name,
        t.relname AS table_name,
        i.relname AS index_name,
        array_agg(a.attname ORDER BY k.i) AS column_names,
        pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
        idx.idx_scan AS scan_count
    FROM pg_index ix
    JOIN pg_class t ON t.oid = ix.indrelid
    JOIN pg_class i ON i.oid = ix.indexrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    JOIN pg_stat_user_indexes idx ON idx.indexrelname = i.relname
    CROSS JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, i)
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
    WHERE n.nspname = 'public'
        AND NOT ix.indisprimary
        AND NOT ix.indisunique
    GROUP BY n.nspname, t.relname, i.relname, i.oid, idx.idx_scan
)
SELECT 
    ic1.table_name,
    ic1.index_name AS indice_1,
    ic1.column_names AS colunas_1,
    ic1.index_size AS tamanho_1,
    ic1.scan_count AS uso_1,
    ic2.index_name AS indice_2,
    ic2.column_names AS colunas_2,
    ic2.index_size AS tamanho_2,
    ic2.scan_count AS uso_2,
    CASE 
        WHEN ic1.column_names = ic2.column_names THEN 'DUPLICADO EXATO'
        WHEN ic1.column_names @> ic2.column_names THEN 'INDICE_1 CONTÉM INDICE_2'
        WHEN ic2.column_names @> ic1.column_names THEN 'INDICE_2 CONTÉM INDICE_1'
        ELSE 'OVERLAP PARCIAL'
    END AS tipo_redundancia,
    CASE 
        WHEN ic1.scan_count < ic2.scan_count THEN 
            'DROP INDEX IF EXISTS ' || ic1.index_name || '; -- Menos usado'
        ELSE 
            'DROP INDEX IF EXISTS ' || ic2.index_name || '; -- Menos usado'
    END AS recomendacao
FROM index_columns ic1
JOIN index_columns ic2 ON 
    ic1.table_name = ic2.table_name 
    AND ic1.index_name < ic2.index_name
    AND (ic1.column_names @> ic2.column_names 
         OR ic2.column_names @> ic1.column_names
         OR ic1.column_names = ic2.column_names)
ORDER BY ic1.table_name, ic1.index_name;

-- =====================================================
-- 4. ÍNDICES MUITO GRANDES COM POUCO USO
-- =====================================================
\echo ''
\echo '========================================='
\echo '4. ÍNDICES GRANDES COM POUCO USO'
\echo '========================================='

SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho,
    idx_scan AS num_utilizacoes,
    ROUND((pg_relation_size(indexrelid)::numeric / 1024 / 1024) / NULLIF(idx_scan, 0), 2) AS mb_por_uso,
    CASE 
        WHEN idx_scan < 100 AND pg_relation_size(indexrelid) > 10485760 THEN 'CANDIDATO FORTE A REMOÇÃO'
        WHEN idx_scan < 1000 AND pg_relation_size(indexrelid) > 52428800 THEN 'AVALIAR NECESSIDADE'
        ELSE 'MANTER'
    END AS recomendacao
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND pg_relation_size(indexrelid) > 5242880  -- Maior que 5MB
ORDER BY 
    mb_por_uso DESC NULLS FIRST,
    pg_relation_size(indexrelid) DESC;

-- =====================================================
-- 5. TABELAS SEM ÍNDICES EM COLUNAS FK
-- =====================================================
\echo ''
\echo '========================================='
\echo '5. FOREIGN KEYS SEM ÍNDICES'
\echo '========================================='

SELECT 
    c.conname AS constraint_name,
    n.nspname AS schema_name,
    t.relname AS table_name,
    array_agg(a.attname ORDER BY k.i) AS fk_columns,
    'CREATE INDEX idx_' || t.relname || '_' || 
        array_to_string(array_agg(a.attname ORDER BY k.i), '_') || 
        ' ON ' || n.nspname || '.' || t.relname || ' (' || 
        array_to_string(array_agg(a.attname ORDER BY k.i), ', ') || ');' AS create_index_cmd
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, i)
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
WHERE c.contype = 'f'  -- Foreign key
    AND n.nspname = 'public'
    AND NOT EXISTS (
        SELECT 1
        FROM pg_index ix
        WHERE ix.indrelid = t.oid
            AND (c.conkey <@ ix.indkey OR c.conkey = ix.indkey)
    )
GROUP BY c.conname, n.nspname, t.relname
ORDER BY n.nspname, t.relname;

-- =====================================================
-- 6. ANÁLISE DE FRAGMENTAÇÃO DOS ÍNDICES
-- =====================================================
\echo ''
\echo '========================================='
\echo '6. FRAGMENTAÇÃO DOS ÍNDICES (BLOAT)'
\echo '========================================='

WITH btree_index_atts AS (
    SELECT 
        nspname,
        relname AS table_name,
        indexrelname AS index_name,
        reltuples,
        relpages,
        indrelid,
        indexrelid,
        indnatts,
        indkey
    FROM pg_index
    JOIN pg_class ON pg_class.oid = pg_index.indexrelid
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
    JOIN pg_stat_user_indexes ON pg_stat_user_indexes.indexrelid = pg_index.indexrelid
    WHERE nspname = 'public'
        AND relpages > 0
),
index_bloat AS (
    SELECT 
        nspname,
        table_name,
        index_name,
        bs*(relpages)::bigint AS real_size,
        bs*(relpages-est_pages)::bigint AS extra_size,
        100 * (relpages-est_pages)::float / relpages AS extra_pct,
        CASE WHEN relpages > est_pages_ff 
            THEN bs*(relpages-est_pages_ff) 
            ELSE 0 
        END AS bloat_size,
        100 * (relpages-est_pages_ff)::float / relpages AS bloat_pct
    FROM (
        SELECT 
            nspname,
            table_name,
            index_name,
            relpages,
            current_setting('block_size')::numeric AS bs,
            CEIL(reltuples*6/bs) AS est_pages,
            CEIL(reltuples*6*1.2/bs) AS est_pages_ff
        FROM btree_index_atts
    ) AS sub
    WHERE relpages > 1
)
SELECT 
    table_name,
    index_name,
    pg_size_pretty(real_size::bigint) AS index_size,
    pg_size_pretty(extra_size::bigint) AS extra_size,
    ROUND(extra_pct::numeric, 2) || '%' AS extra_pct,
    pg_size_pretty(bloat_size::bigint) AS bloat_size,
    ROUND(bloat_pct::numeric, 2) || '%' AS bloat_pct,
    CASE 
        WHEN bloat_pct > 50 THEN 'REINDEX URGENTE'
        WHEN bloat_pct > 30 THEN 'REINDEX RECOMENDADO'
        WHEN bloat_pct > 20 THEN 'MONITORAR'
        ELSE 'OK'
    END AS acao_recomendada,
    'REINDEX INDEX CONCURRENTLY ' || index_name || ';' AS comando_reindex
FROM index_bloat
WHERE bloat_pct > 20
ORDER BY bloat_size DESC;

-- =====================================================
-- 7. ÍNDICES EM COLUNAS COM BAIXA CARDINALIDADE
-- =====================================================
\echo ''
\echo '========================================='
\echo '7. ÍNDICES EM COLUNAS DE BAIXA CARDINALIDADE'
\echo '========================================='

WITH column_stats AS (
    SELECT 
        schemaname,
        tablename,
        attname,
        n_distinct,
        null_frac,
        correlation
    FROM pg_stats
    WHERE schemaname = 'public'
),
indexed_columns AS (
    SELECT DISTINCT
        n.nspname AS schema_name,
        t.relname AS table_name,
        a.attname AS column_name,
        i.relname AS index_name
    FROM pg_index ix
    JOIN pg_class t ON t.oid = ix.indrelid
    JOIN pg_class i ON i.oid = ix.indexrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
    WHERE n.nspname = 'public'
        AND NOT ix.indisprimary
)
SELECT 
    ic.table_name,
    ic.column_name,
    ic.index_name,
    cs.n_distinct AS valores_distintos,
    ROUND(cs.null_frac * 100, 2) || '%' AS pct_nulos,
    ROUND(ABS(cs.correlation) * 100, 2) || '%' AS correlacao,
    CASE 
        WHEN cs.n_distinct BETWEEN 0 AND 1 THEN 'MUITO BAIXA - ' || ROUND(cs.n_distinct * 100, 2) || '% distintos'
        WHEN cs.n_distinct BETWEEN -1 AND 0 THEN 'BAIXA - aprox ' || ROUND(ABS(cs.n_distinct * 100), 0) || ' valores'
        WHEN cs.n_distinct < -1 THEN 'MÉDIA - aprox ' || ROUND(ABS(cs.n_distinct), 0) || ' valores'
        ELSE 'ALTA - ' || cs.n_distinct || ' valores'
    END AS cardinalidade,
    CASE 
        WHEN cs.n_distinct BETWEEN -10 AND 10 THEN 'CONSIDERAR REMOÇÃO DO ÍNDICE'
        WHEN cs.n_distinct BETWEEN -100 AND -10 THEN 'AVALIAR NECESSIDADE'
        ELSE 'MANTER'
    END AS recomendacao
FROM indexed_columns ic
JOIN column_stats cs ON cs.tablename = ic.table_name AND cs.attname = ic.column_name
WHERE cs.n_distinct BETWEEN -100 AND 100
ORDER BY ABS(cs.n_distinct) ASC;

-- =====================================================
-- 8. SUGESTÕES DE NOVOS ÍNDICES BASEADO EM QUERIES
-- =====================================================
\echo ''
\echo '========================================='
\echo '8. QUERIES LENTAS SEM ÍNDICES ADEQUADOS'
\echo '========================================='

SELECT 
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_ms,
    ROUND(mean_exec_time::numeric, 2) AS mean_ms,
    ROUND(max_exec_time::numeric, 2) AS max_ms,
    LEFT(query, 100) AS query_sample,
    CASE 
        WHEN query ILIKE '%WHERE%' AND query ILIKE '%=%' THEN 'POSSÍVEL ÍNDICE FALTANDO'
        WHEN query ILIKE '%JOIN%' THEN 'VERIFICAR ÍNDICES NAS JOINS'
        WHEN query ILIKE '%ORDER BY%' THEN 'CONSIDERAR ÍNDICE PARA ORDENAÇÃO'
        ELSE 'ANALISAR MANUALMENTE'
    END AS possivel_otimizacao
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- Queries com média > 100ms
    AND query NOT ILIKE '%pg_%'  -- Ignora queries do sistema
    AND query NOT ILIKE '%information_schema%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- =====================================================
-- 9. RESUMO E ESTATÍSTICAS GERAIS
-- =====================================================
\echo ''
\echo '========================================='
\echo '9. RESUMO EXECUTIVO'
\echo '========================================='

WITH stats AS (
    SELECT 
        COUNT(*) FILTER (WHERE idx_scan = 0) AS indices_nao_usados,
        COUNT(*) FILTER (WHERE idx_scan > 0 AND idx_scan < 100) AS indices_pouco_usados,
        COUNT(*) FILTER (WHERE idx_scan >= 100) AS indices_bem_usados,
        COUNT(*) AS total_indices,
        pg_size_pretty(SUM(pg_relation_size(indexrelid)) FILTER (WHERE idx_scan = 0)) AS espaco_desperdicado,
        pg_size_pretty(SUM(pg_relation_size(indexrelid))) AS espaco_total_indices
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
)
SELECT 
    total_indices AS "Total de Índices",
    indices_nao_usados AS "Nunca Usados",
    indices_pouco_usados AS "Pouco Usados (<100)",
    indices_bem_usados AS "Bem Usados (>=100)",
    espaco_total_indices AS "Espaço Total",
    espaco_desperdicado AS "Espaço Desperdiçado",
    ROUND(indices_nao_usados::numeric * 100 / total_indices, 2) || '%' AS "% Não Usados"
FROM stats;

-- =====================================================
-- 10. SCRIPT DE LIMPEZA GERADO
-- =====================================================
\echo ''
\echo '========================================='
\echo '10. SCRIPT DE LIMPEZA SUGERIDO'
\echo '========================================='

\echo '-- ATENÇÃO: Revise cada comando antes de executar!'
\echo '-- Execute em horário de baixa demanda'
\echo '-- Faça backup antes de executar'
\echo ''

-- Gera comandos DROP para índices não usados
SELECT '-- Índice nunca usado: ' || indexname || ' (' || pg_size_pretty(pg_relation_size(indexrelid)) || ')' || E'\n' ||
       'DROP INDEX IF EXISTS ' || indexname || ';' AS comando
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND idx_scan = 0
    AND indexrelname NOT LIKE '%_pkey'
    AND indexrelname NOT LIKE '%_unique'
ORDER BY pg_relation_size(indexrelid) DESC;

\echo ''
\echo '-- Comandos REINDEX para índices fragmentados:'

-- Gera comandos REINDEX para índices com bloat
SELECT 'REINDEX INDEX CONCURRENTLY ' || indexname || '; -- Fragmentação detectada' AS comando
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND idx_scan > 0
ORDER BY indexname;

\echo ''
\echo '========================================='
\echo 'FIM DA ANÁLISE'
\echo '========================================='