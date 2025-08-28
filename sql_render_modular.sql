-- =====================================================
-- SCRIPT MODULAR PARA RENDER - EXECUTE POR PARTES
-- Data: 2025-01-29
-- =====================================================

-- =====================================================
-- PARTE 1: ADICIONAR TODOS OS CAMPOS DE UMA VEZ
-- =====================================================
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ABERTO' NOT NULL,
ADD COLUMN IF NOT EXISTS nf_cd BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS data_embarque DATE,
ADD COLUMN IF NOT EXISTS cidade_normalizada VARCHAR(120),
ADD COLUMN IF NOT EXISTS uf_normalizada VARCHAR(2),
ADD COLUMN IF NOT EXISTS codigo_ibge VARCHAR(10),
ADD COLUMN IF NOT EXISTS separacao_impressa BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS separacao_impressa_em TIMESTAMP,
ADD COLUMN IF NOT EXISTS separacao_impressa_por VARCHAR(100);

-- =====================================================
-- PARTE 2: ÍNDICES ESSENCIAIS (execute um por vez)
-- =====================================================

-- 2.1 - Índice principal para agrupamento
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_lote_sync 
ON separacao(separacao_lote_id, sincronizado_nf)
WHERE separacao_lote_id IS NOT NULL;

-- 2.2 - Índice para num_pedido (IMPORTANTE!)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_num_pedido
ON separacao(num_pedido)
WHERE num_pedido IS NOT NULL;

-- 2.3 - Índice composto num_pedido + sincronizado
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_pedido_sync
ON separacao(num_pedido, sincronizado_nf)
WHERE num_pedido IS NOT NULL;

-- 2.4 - Índice para estoque projetado (crítico)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_estoque_projetado
ON separacao(cod_produto, expedicao)
WHERE sincronizado_nf = FALSE 
AND expedicao IS NOT NULL;

-- 2.5 - Índice lote + status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_lote_status 
ON separacao(separacao_lote_id, status)
WHERE separacao_lote_id IS NOT NULL;

-- 2.6 - Índice simples para status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_status 
ON separacao(status);

-- 2.7 - Índice para NF
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_nf 
ON separacao(numero_nf, sincronizado_nf)
WHERE numero_nf IS NOT NULL;

-- 2.8 - Índice para expedição + produto (visão por data)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_expedicao_produto
ON separacao(expedicao, cod_produto)
WHERE sincronizado_nf = FALSE;

-- 2.9 - Índice para CNPJ
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_cnpj
ON separacao(cnpj_cpf, sincronizado_nf)
WHERE cnpj_cpf IS NOT NULL;

-- =====================================================
-- PARTE 3: VERIFICAÇÃO (execute para confirmar)
-- =====================================================

-- 3.1 - Verificar campos criados
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'separacao'
AND column_name IN ('status', 'nf_cd', 'data_embarque', 'cidade_normalizada', 
                    'uf_normalizada', 'codigo_ibge', 'separacao_impressa')
ORDER BY ordinal_position;

-- 3.2 - Verificar índices criados  
SELECT indexname
FROM pg_indexes
WHERE tablename = 'separacao'
AND indexname LIKE 'idx_sep_%'
ORDER BY indexname;

-- 3.3 - Estatísticas básicas
SELECT 
    COUNT(*) as total_registros,
    COUNT(DISTINCT num_pedido) as total_pedidos,
    COUNT(DISTINCT separacao_lote_id) as total_lotes,
    COUNT(*) FILTER (WHERE sincronizado_nf = FALSE) as nao_sincronizados
FROM separacao;