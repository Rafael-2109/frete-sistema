-- VACUUM ANALYZE — Tabelas com bloat >10%
-- Diagnosticado em 2026-02-28
-- Executar via Render Shell (psql) ou qualquer client SQL com permissao de escrita
--
-- NOTA: VACUUM nao pode rodar dentro de transacao.
--       Se usar psql, execute cada comando separadamente.
--       VACUUM nao bloqueia leituras (safe para producao).

-- 1. movimentacao_estoque (16.5% bloat, 12222 dead tuples)
VACUUM ANALYZE movimentacao_estoque;

-- 2. extrato_item (16.2% bloat, 3611 dead tuples)
VACUUM ANALYZE extrato_item;

-- 3. nf_devolucao (16.8% bloat, 846 dead tuples)
VACUUM ANALYZE nf_devolucao;

-- 4. baixa_titulo_item (12.5% bloat, 678 dead tuples)
VACUUM ANALYZE baixa_titulo_item;

-- 5. conhecimento_transporte (12.0% bloat, 661 dead tuples)
VACUUM ANALYZE conhecimento_transporte;

-- 6. entregas_monitoradas (11.8% bloat, 1662 dead tuples)
VACUUM ANALYZE entregas_monitoradas;

-- 7. comprovante_pagamento_boleto (11.6% bloat, 803 dead tuples)
VACUUM ANALYZE comprovante_pagamento_boleto;

-- Verificacao pos-VACUUM:
SELECT
    relname AS tabela,
    n_live_tup AS live,
    n_dead_tup AS dead,
    CASE WHEN n_live_tup + n_dead_tup > 0
         THEN ROUND(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 1)
         ELSE 0
    END AS bloat_pct,
    last_vacuum,
    last_autovacuum,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
WHERE relname IN (
    'movimentacao_estoque',
    'extrato_item',
    'nf_devolucao',
    'baixa_titulo_item',
    'conhecimento_transporte',
    'entregas_monitoradas',
    'comprovante_pagamento_boleto'
)
ORDER BY n_dead_tup DESC;
