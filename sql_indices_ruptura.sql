-- ==============================================================================
-- SQL para criar índices otimizados para as queries de ruptura
-- Data: 2025-01-29
-- ==============================================================================

-- ==============================================================================
-- PARTE 1: ÍNDICES PARA CARTEIRA PRINCIPAL (queries de ruptura)
-- ==============================================================================

-- Índice para buscar itens por pedido com saldo > 0
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_pedido_saldo
ON carteira_principal(num_pedido, qtd_saldo_produto_pedido)
WHERE qtd_saldo_produto_pedido > 0;

-- Índice para buscar itens por produto + pedido
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_produto_pedido
ON carteira_principal(cod_produto, num_pedido);

-- Índice composto para lookup de estoque por produto e data
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_produto_expedicao
ON carteira_principal(cod_produto, expedicao)
WHERE qtd_saldo_produto_pedido > 0;

-- ==============================================================================
-- PARTE 2: ÍNDICES PARA SEPARACAO (queries de cardex e ruptura)
-- ==============================================================================

-- Índice principal para cardex detalhado: produto + sincronizado + qtd
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_cardex_produto
ON separacao(cod_produto, sincronizado_nf, qtd_saldo)
WHERE sincronizado_nf = FALSE AND qtd_saldo > 0;

-- Índice para buscar separações por produto com dados de expedição
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_produto_expedicao_sync
ON separacao(cod_produto, expedicao, sincronizado_nf)
WHERE sincronizado_nf = FALSE;

-- Índice para agrupamento por lote + pedido + produto
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_lote_pedido_produto
ON separacao(separacao_lote_id, num_pedido, cod_produto)
WHERE sincronizado_nf = FALSE;

-- ==============================================================================
-- PARTE 3: ÍNDICES PARA PROGRAMACAO_PRODUCAO (análise de ruptura)
-- ==============================================================================

-- Índice para buscar produções futuras por produto
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_producao_produto_data
ON programacao_producao(cod_produto, data_programacao, qtd_programada)
WHERE data_programacao >= CURRENT_DATE;

-- Índice composto para agregação de produção
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_producao_agregacao
ON programacao_producao(cod_produto, data_programacao)
WHERE qtd_programada > 0 AND data_programacao >= CURRENT_DATE;

-- ==============================================================================
-- PARTE 4: ANÁLISE DE ÍNDICES EXISTENTES E LIMPEZA
-- ==============================================================================

-- Verificar índices duplicados ou não utilizados
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND tablename IN ('carteira_principal', 'separacao', 'programacao_producao')
ORDER BY idx_scan ASC, index_size DESC;

-- ==============================================================================
-- PARTE 5: VACUUM E ANALYZE APÓS CRIAÇÃO DOS ÍNDICES
-- ==============================================================================

-- Atualizar estatísticas para o otimizador
ANALYZE carteira_principal;
ANALYZE separacao;
ANALYZE programacao_producao;

-- Vacuum para liberar espaço e atualizar visibility map
VACUUM (ANALYZE) carteira_principal;
VACUUM (ANALYZE) separacao;
VACUUM (ANALYZE) programacao_producao;

-- ==============================================================================
-- VERIFICAÇÃO FINAL
-- ==============================================================================

-- Listar todos os índices criados
SELECT 
    i.relname AS index_name,
    t.relname AS table_name,
    pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
    idx.indisprimary AS is_primary,
    idx.indisunique AS is_unique
FROM pg_class i
JOIN pg_index idx ON i.oid = idx.indexrelid
JOIN pg_class t ON t.oid = idx.indrelid
WHERE t.relname IN ('carteira_principal', 'separacao', 'programacao_producao')
    AND i.relkind = 'i'
ORDER BY t.relname, i.relname;

-- ==============================================================================
-- NOTAS IMPORTANTES:
-- ==============================================================================
-- 1. Usar CONCURRENTLY para não bloquear operações durante criação
-- 2. Índices parciais (WHERE) são mais eficientes para queries específicas
-- 3. Ordem das colunas no índice importa: mais seletiva primeiro
-- 4. Monitorar uso com pg_stat_user_indexes regularmente
-- 5. Remover índices não utilizados (idx_scan = 0 após período)
-- ==============================================================================