-- =============================================================================
-- VACUUM ANALYZE — Tabelas criticas com dead tuple ratio > 10%
-- Avaliacao: 01/03/2026
-- Executar via: Render Shell (psql)
-- =============================================================================
--
-- NOTA: VACUUM nao pode rodar dentro de transacao.
-- No Render Shell, executar cada comando individualmente.
--
-- Verificar estado ANTES:
-- SELECT relname, n_live_tup, n_dead_tup,
--        ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 2) AS dead_ratio,
--        last_autovacuum
-- FROM pg_stat_user_tables
-- WHERE relname IN ('picking_recebimento_quality_check','embarques',
--                   'baixa_titulo_item','embarque_itens','controle_portaria',
--                   'separacao','lancamento_comprovante','fretes')
-- ORDER BY dead_ratio DESC;

-- 20.09% dead tuples
VACUUM ANALYZE picking_recebimento_quality_check;

-- 15.71% dead tuples
VACUUM ANALYZE embarques;

-- 12.45% dead tuples (NUNCA recebeu autovacuum)
VACUUM ANALYZE baixa_titulo_item;

-- 11.93% dead tuples (NUNCA recebeu autovacuum)
VACUUM ANALYZE embarque_itens;

-- 11.33% dead tuples (NUNCA recebeu autovacuum)
VACUUM ANALYZE controle_portaria;

-- 10.84% dead tuples
VACUUM ANALYZE separacao;

-- 10.16% dead tuples (NUNCA recebeu autovacuum)
VACUUM ANALYZE lancamento_comprovante;

-- 10.20% dead tuples (NUNCA recebeu autovacuum)
VACUUM ANALYZE fretes;

-- Verificar estado DEPOIS:
-- SELECT relname, n_live_tup, n_dead_tup,
--        ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 2) AS dead_ratio,
--        last_autovacuum
-- FROM pg_stat_user_tables
-- WHERE relname IN ('picking_recebimento_quality_check','embarques',
--                   'baixa_titulo_item','embarque_itens','controle_portaria',
--                   'separacao','lancamento_comprovante','fretes')
-- ORDER BY dead_ratio DESC;
