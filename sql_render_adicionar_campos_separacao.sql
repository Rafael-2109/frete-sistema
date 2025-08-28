-- =====================================================
-- SCRIPT SQL PARA ADICIONAR CAMPOS EM SEPARACAO - RENDER
-- Data: 2025-01-29
-- Objetivo: Adicionar campos para eliminar PreSeparacaoItem e tornar Pedido uma VIEW
-- =====================================================

-- 1. ADICIONAR NOVOS CAMPOS EM SEPARACAO
-- =====================================================

-- Campo status (PREVISAO, ABERTO, FATURADO)
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ABERTO' NOT NULL;

-- Campo nf_cd (NF voltou para o CD)
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS nf_cd BOOLEAN DEFAULT FALSE NOT NULL;

-- Campo data_embarque
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS data_embarque DATE;

-- Campos de normalização
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS cidade_normalizada VARCHAR(120);

ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS uf_normalizada VARCHAR(2);

ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS codigo_ibge VARCHAR(10);

-- Campos de controle de impressão
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS separacao_impressa BOOLEAN DEFAULT FALSE NOT NULL;

ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS separacao_impressa_em TIMESTAMP;

ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS separacao_impressa_por VARCHAR(100);


-- 2. CRIAR ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índice principal: lote + sincronização
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_lote_sync 
ON separacao(separacao_lote_id, sincronizado_nf)
WHERE separacao_lote_id IS NOT NULL;

-- Índice: lote + status (lote primeiro pois é mais seletivo)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_lote_status 
ON separacao(separacao_lote_id, status)
WHERE separacao_lote_id IS NOT NULL;

-- Índice simples para queries só por status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_status 
ON separacao(status);

-- Índice para NF
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_nf 
ON separacao(numero_nf, sincronizado_nf)
WHERE numero_nf IS NOT NULL;

-- Índice parcial para itens não sincronizados (carteira/estoque)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_nao_sincronizado
ON separacao(separacao_lote_id, cod_produto)
WHERE sincronizado_nf = FALSE;

-- Índice para queries de expedição
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_expedicao
ON separacao(expedicao, sincronizado_nf)
WHERE expedicao IS NOT NULL;

-- ÍNDICE CRÍTICO PARA ESTOQUE PROJETADO: produto + expedição
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_estoque_projetado
ON separacao(cod_produto, expedicao)
WHERE sincronizado_nf = FALSE 
AND expedicao IS NOT NULL;

-- Índice alternativo para visão por data (todos produtos de uma data)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_expedicao_produto
ON separacao(expedicao, cod_produto)
WHERE sincronizado_nf = FALSE;


-- 3. ATUALIZAR ESTATÍSTICAS
-- =====================================================
ANALYZE separacao;


-- 4. VERIFICAR CAMPOS CRIADOS
-- =====================================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'separacao'
AND column_name IN (
    'status', 'nf_cd', 'data_embarque', 
    'cidade_normalizada', 'uf_normalizada', 'codigo_ibge',
    'separacao_impressa', 'separacao_impressa_em', 'separacao_impressa_por'
)
ORDER BY ordinal_position;


-- 5. VERIFICAR ÍNDICES CRIADOS
-- =====================================================
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'separacao'
AND indexname LIKE 'idx_sep_%'
ORDER BY indexname;


-- 6. ESTATÍSTICAS DA TABELA
-- =====================================================
SELECT 
    'Total de registros:' as info,
    COUNT(*) as valor
FROM separacao
UNION ALL
SELECT 
    'Registros com lote:',
    COUNT(*)
FROM separacao
WHERE separacao_lote_id IS NOT NULL
UNION ALL
SELECT 
    'Registros não sincronizados:',
    COUNT(*)
FROM separacao
WHERE sincronizado_nf = FALSE;

-- FIM DO SCRIPT
-- =====================================================