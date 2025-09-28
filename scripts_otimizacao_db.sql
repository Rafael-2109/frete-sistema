-- ========================================================
-- SCRIPTS DE OTIMIZAÇÃO DO BANCO DE DADOS
-- PostgreSQL 16
-- Data: 09/05/2025
-- ========================================================

-- ========================================================
-- PARTE 1: CRIAÇÃO DE ÍNDICES DE PERFORMANCE
-- ========================================================

-- Nota: Usando CONCURRENTLY para não bloquear a tabela durante criação
-- Este processo pode demorar mais, mas não afeta operações em produção

-- CarteiraPrincipal
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_pedido_produto 
ON carteira_principal(num_pedido, cod_produto);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_cnpj 
ON carteira_principal(cnpj_cpf);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_vendedor 
ON carteira_principal(vendedor) 
WHERE vendedor IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_expedicao 
ON carteira_principal(expedicao) 
WHERE expedicao IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_lote 
ON carteira_principal(separacao_lote_id) 
WHERE separacao_lote_id IS NOT NULL;

-- FaturamentoProduto
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_origem_produto 
ON faturamento_produto(origem, cod_produto);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_status 
ON faturamento_produto(status_nf);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_data 
ON faturamento_produto(data_fatura);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_cliente 
ON faturamento_produto(cnpj_cliente);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_vendedor 
ON faturamento_produto(vendedor)
WHERE vendedor IS NOT NULL;

-- Separacao
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_separacao_pedido_produto 
ON separacao(num_pedido, cod_produto);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_separacao_sincronizado 
ON separacao(sincronizado_nf);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_separacao_status 
ON separacao(status) 
WHERE status IN ('PREVISAO', 'ABERTO', 'COTADO');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_separacao_lote_pedido 
ON separacao(separacao_lote_id, num_pedido) 
WHERE separacao_lote_id IS NOT NULL;

-- RelatorioFaturamentoImportado
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relatorio_nf 
ON relatorio_faturamento_importado(numero_nf);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relatorio_ativo 
ON relatorio_faturamento_importado(ativo);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relatorio_cnpj 
ON relatorio_faturamento_importado(cnpj_cliente);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relatorio_data 
ON relatorio_faturamento_importado(data_fatura)
WHERE data_fatura IS NOT NULL;

-- ========================================================
-- PARTE 2: ATUALIZAÇÃO DE ESTATÍSTICAS
-- ========================================================

-- Atualizar estatísticas das tabelas para o otimizador de queries
ANALYZE carteira_principal;
ANALYZE faturamento_produto;
ANALYZE separacao;
ANALYZE relatorio_faturamento_importado;

-- ========================================================
-- PARTE 3: QUERIES DE MONITORAMENTO
-- ========================================================

-- 3.1 Verificar se a extensão pg_stat_statements está habilitada
-- (necessário para monitorar queries lentas)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 3.2 Verificar queries lentas (requer pg_stat_statements habilitado)
-- Descomente e execute separadamente após habilitar a extensão
/*
SELECT 
    query,
    calls,
    total_exec_time as total_time,
    mean_exec_time as mean_time,
    max_exec_time as max_time
FROM pg_stat_statements
WHERE query LIKE '%carteira_principal%'
   OR query LIKE '%faturamento_produto%'
   OR query LIKE '%separacao%'
ORDER BY mean_exec_time DESC
LIMIT 20;
*/

-- 3.3 Verificar índices não utilizados (PostgreSQL 16 usa 'relname')
SELECT 
    schemaname,
    relname as tablename,
    indexrelname as indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND idx_scan = 0
ORDER BY relname, indexrelname;

-- 3.4 Verificar tamanho das tabelas e seus índices
SELECT 
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_indexes_size(relid)) AS indexes_size,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(relid) DESC;

-- 3.5 Verificar índices duplicados ou redundantes
WITH index_info AS (
    SELECT
        schemaname,
        array_to_string(array_agg(attname ORDER BY attnum), ', ') AS columns
    FROM pg_index i
    JOIN pg_class c ON c.oid = i.indexrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_stat_user_indexes ui ON ui.indexrelid = i.indexrelid
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    WHERE n.nspname = 'public'
    GROUP BY schemaname, indexname
)
SELECT 
    relname,
    columns,
    array_agg(indexname) as indices_on_same_columns,
    count(*) as index_count
FROM index_info
GROUP BY relname, columns
HAVING count(*) > 1
ORDER BY relname, columns;

-- 3.6 Verificar estatísticas de cache hit ratio (ideal > 99%)
SELECT 
    schemaname,
    relname,
    heap_blks_read,
    heap_blks_hit,
    CASE 
        WHEN heap_blks_read + heap_blks_hit = 0 THEN 0
        ELSE round(100.0 * heap_blks_hit / (heap_blks_read + heap_blks_hit), 2)
    END as cache_hit_ratio
FROM pg_statio_user_tables
WHERE schemaname = 'public'
    AND (heap_blks_read > 0 OR heap_blks_hit > 0)
ORDER BY heap_blks_read + heap_blks_hit DESC;

-- 3.7 Verificar bloat nas tabelas (espaço desperdiçado)
SELECT
    schemaname,
    relname,
    pg_size_pretty(pg_relation_size(schemaname||'.'||relname)) AS table_size,
    n_dead_tup AS dead_tuples,
    n_live_tup AS live_tuples,
    CASE 
        WHEN n_live_tup > 0 THEN round(100.0 * n_dead_tup / n_live_tup, 2)
        ELSE 0
    END AS dead_tuple_percent
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- 3.8 Verificar configurações importantes do PostgreSQL
SHOW shared_buffers;
SHOW effective_cache_size;
SHOW work_mem;
SHOW maintenance_work_mem;
SHOW max_connections;
SHOW random_page_cost;
SHOW effective_io_concurrency;

-- ========================================================
-- PARTE 4: LIMPEZA E MANUTENÇÃO (EXECUTAR COM CUIDADO)
-- ========================================================

-- 4.1 Reindexar tabelas com alto bloat (executar fora do horário de pico)
-- REINDEX TABLE CONCURRENTLY carteira_principal;
-- REINDEX TABLE CONCURRENTLY faturamento_produto;
-- REINDEX TABLE CONCURRENTLY separacao;
-- REINDEX TABLE CONCURRENTLY relatorio_faturamento_importado;

-- 4.2 Vacuum full para recuperar espaço (BLOQUEIA A TABELA - executar em manutenção)
-- VACUUM FULL ANALYZE carteira_principal;
-- VACUUM FULL ANALYZE faturamento_produto;
-- VACUUM FULL ANALYZE separacao;
-- VACUUM FULL ANALYZE relatorio_faturamento_importado;

-- 4.3 Vacuum normal (não bloqueia, mas menos agressivo)
VACUUM ANALYZE carteira_principal;
VACUUM ANALYZE faturamento_produto;
VACUUM ANALYZE separacao;
VACUUM ANALYZE relatorio_faturamento_importado;

-- ========================================================
-- PARTE 5: VERIFICAÇÃO FINAL
-- ========================================================

-- Listar todos os índices criados
SELECT 
    schemaname,
    relname,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND relname IN ('carteira_principal', 'faturamento_produto', 'separacao', 'relatorio_faturamento_importado')
ORDER BY relname, indexname;

-- Verificar se todos os índices foram criados com sucesso
SELECT 
    'Índices criados com sucesso!' as status,
    count(*) as total_indices
FROM pg_indexes
WHERE schemaname = 'public'
    AND indexname LIKE 'idx_%'
    AND relname IN ('carteira_principal', 'faturamento_produto', 'separacao', 'relatorio_faturamento_importado');

-- ========================================================
-- FIM DO SCRIPT DE OTIMIZAÇÃO
-- ========================================================