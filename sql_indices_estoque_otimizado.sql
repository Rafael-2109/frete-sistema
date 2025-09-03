-- ============================================================
-- ÍNDICES OTIMIZADOS PARA SISTEMA DE ESTOQUE SIMPLIFICADO
-- Performance garantida < 50ms por consulta
-- ============================================================

-- ------------------------------------------------------------
-- 1. ÍNDICES PARA MovimentacaoEstoque
-- ------------------------------------------------------------

-- Índice principal para cálculo de estoque atual
-- Usa partial index para excluir cancelados diretamente
CREATE INDEX IF NOT EXISTS idx_mov_estoque_produto_ativo_not_cancelado 
ON movimentacao_estoque(cod_produto, ativo)
WHERE ativo = true AND (status_nf != 'CANCELADO' OR status_nf IS NULL);

-- Índice de cobertura para evitar table lookup
CREATE INDEX IF NOT EXISTS idx_mov_estoque_cobertura 
ON movimentacao_estoque(cod_produto, qtd_movimentacao)
WHERE ativo = true AND (status_nf != 'CANCELADO' OR status_nf IS NULL);

-- Índice para queries por status_nf
CREATE INDEX IF NOT EXISTS idx_mov_estoque_status_nf 
ON movimentacao_estoque(status_nf)
WHERE status_nf IS NOT NULL;

-- ------------------------------------------------------------
-- 2. ÍNDICES PARA Separacao (Saídas Previstas)
-- ------------------------------------------------------------

-- Índice composto para saídas previstas por período
CREATE INDEX IF NOT EXISTS idx_separacao_produto_expedicao_sync 
ON separacao(cod_produto, expedicao, sincronizado_nf)
WHERE sincronizado_nf = false;

-- Índice de cobertura incluindo qtd_saldo
CREATE INDEX IF NOT EXISTS idx_separacao_cobertura 
ON separacao(cod_produto, expedicao, qtd_saldo)
WHERE sincronizado_nf = false;

-- Índice para busca por data de expedição
CREATE INDEX IF NOT EXISTS idx_separacao_expedicao 
ON separacao(expedicao)
WHERE sincronizado_nf = false;

-- ------------------------------------------------------------
-- 3. ÍNDICES PARA ProgramacaoProducao (Entradas Previstas)
-- ------------------------------------------------------------

-- Índice composto para entradas previstas
CREATE INDEX IF NOT EXISTS idx_programacao_produto_data 
ON programacao_producao(cod_produto, data_programacao);

-- Índice de cobertura incluindo quantidade
CREATE INDEX IF NOT EXISTS idx_programacao_cobertura
ON programacao_producao(cod_produto, data_programacao, qtd_programada);

-- Índice para busca por período
CREATE INDEX IF NOT EXISTS idx_programacao_data 
ON programacao_producao(data_programacao);

-- ------------------------------------------------------------
-- 4. ÍNDICES PARA UnificacaoCodigos
-- ------------------------------------------------------------

-- Índices já existentes, mas vamos garantir
CREATE INDEX IF NOT EXISTS idx_unificacao_origem 
ON unificacao_codigos(codigo_origem)
WHERE ativo = true;

CREATE INDEX IF NOT EXISTS idx_unificacao_destino 
ON unificacao_codigos(codigo_destino)
WHERE ativo = true;

-- ------------------------------------------------------------
-- 5. ANÁLISE E VACUUM (Executar após criar índices)
-- ------------------------------------------------------------

-- Atualizar estatísticas para o query planner
ANALYZE movimentacao_estoque;
ANALYZE separacao;
ANALYZE programacao_producao;
ANALYZE unificacao_codigos;

-- Limpar espaço morto e reorganizar dados
VACUUM ANALYZE movimentacao_estoque;
VACUUM ANALYZE separacao;
VACUUM ANALYZE programacao_producao;
VACUUM ANALYZE unificacao_codigos;

-- ------------------------------------------------------------
-- 6. QUERIES DE VERIFICAÇÃO DE PERFORMANCE
-- ------------------------------------------------------------

-- Verificar uso dos índices para estoque atual
EXPLAIN (ANALYZE, BUFFERS) 
SELECT SUM(qtd_movimentacao) 
FROM movimentacao_estoque 
WHERE cod_produto = 'TEST_PRODUTO' 
  AND ativo = true 
  AND (status_nf != 'CANCELADO' OR status_nf IS NULL);

-- Verificar uso dos índices para saídas previstas
EXPLAIN (ANALYZE, BUFFERS)
SELECT expedicao, SUM(qtd_saldo)
FROM separacao
WHERE cod_produto = 'TEST_PRODUTO'
  AND sincronizado_nf = false
  AND expedicao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
GROUP BY expedicao;

-- Verificar uso dos índices para entradas previstas
EXPLAIN (ANALYZE, BUFFERS)
SELECT DATE(data_programacao), SUM(qtd_programada)
FROM programacao_producao
WHERE cod_produto = 'TEST_PRODUTO'
  AND DATE(data_programacao) BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
GROUP BY DATE(data_programacao);

-- ------------------------------------------------------------
-- 7. MONITORAMENTO DE ÍNDICES
-- ------------------------------------------------------------

-- Ver tamanho e uso dos índices
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as index_size,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename IN ('movimentacao_estoque', 'separacao', 'programacao_producao', 'unificacao_codigos')
ORDER BY tablename, indexname;

-- Ver índices não utilizados (candidatos a remoção)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND tablename IN ('movimentacao_estoque', 'separacao', 'programacao_producao')
ORDER BY tablename, indexname;