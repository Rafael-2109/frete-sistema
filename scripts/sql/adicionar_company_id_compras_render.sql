-- ==========================================================================================================
-- SCRIPT SQL PARA ADICIONAR CAMPO company_id NAS TABELAS DE COMPRAS
-- Execução: Render PostgreSQL Shell
-- ==========================================================================================================

-- ==========================================================================================================
-- PASSO 1: ADICIONAR COLUNAS company_id
-- ==========================================================================================================

-- Requisição de Compras
ALTER TABLE requisicao_compras
ADD COLUMN IF NOT EXISTS company_id VARCHAR(100);

-- Pedido de Compras
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS company_id VARCHAR(100);

-- Alocação de Compras
ALTER TABLE requisicao_compra_alocacao
ADD COLUMN IF NOT EXISTS company_id VARCHAR(100);

-- Histórico de Requisição
ALTER TABLE historico_requisicao_compras
ADD COLUMN IF NOT EXISTS company_id VARCHAR(100);

-- Histórico de Pedido
ALTER TABLE historico_pedido_compras
ADD COLUMN IF NOT EXISTS company_id VARCHAR(100);


-- ==========================================================================================================
-- PASSO 2: CRIAR ÍNDICES PARA PERFORMANCE
-- ==========================================================================================================

-- Índice composto: empresa + num_requisicao (para filtros)
CREATE INDEX IF NOT EXISTS idx_requisicao_empresa
ON requisicao_compras(company_id, num_requisicao);

-- Índice composto: empresa + num_pedido (para filtros)
CREATE INDEX IF NOT EXISTS idx_pedido_empresa
ON pedido_compras(company_id, num_pedido);

-- Índice simples: empresa (para alocações)
CREATE INDEX IF NOT EXISTS idx_alocacao_empresa
ON requisicao_compra_alocacao(company_id);


-- ==========================================================================================================
-- PASSO 3: REMOVER CONSTRAINTS ANTIGAS E CRIAR NOVAS
-- ==========================================================================================================

-- Requisição de Compras: Remover constraint antiga (num_requisicao + cod_produto)
ALTER TABLE requisicao_compras
DROP CONSTRAINT IF EXISTS uq_requisicao_produto;

-- Requisição de Compras: Criar nova constraint (num_requisicao + cod_produto + company_id)
ALTER TABLE requisicao_compras
ADD CONSTRAINT uq_requisicao_produto_empresa
UNIQUE (num_requisicao, cod_produto, company_id);

-- Pedido de Compras: Remover constraint antiga (num_pedido + cod_produto)
ALTER TABLE pedido_compras
DROP CONSTRAINT IF EXISTS uq_pedido_compras_num_cod_produto;

-- Pedido de Compras: Criar nova constraint (num_pedido + cod_produto + company_id)
ALTER TABLE pedido_compras
ADD CONSTRAINT uq_pedido_compras_num_cod_produto_empresa
UNIQUE (num_pedido, cod_produto, company_id);


-- ==========================================================================================================
-- PASSO 4: VERIFICAR COLUNAS CRIADAS
-- ==========================================================================================================

SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_name IN (
    'requisicao_compras',
    'pedido_compras',
    'requisicao_compra_alocacao',
    'historico_requisicao_compras',
    'historico_pedido_compras'
)
AND column_name = 'company_id'
ORDER BY table_name;


-- ==========================================================================================================
-- PASSO 5: VERIFICAR ÍNDICES CRIADOS
-- ==========================================================================================================

SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_requisicao_empresa',
    'idx_pedido_empresa',
    'idx_alocacao_empresa'
)
ORDER BY tablename, indexname;


-- ==========================================================================================================
-- PASSO 6: VERIFICAR CONSTRAINTS CRIADAS
-- ==========================================================================================================

SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conname IN (
    'uq_requisicao_produto_empresa',
    'uq_pedido_compras_num_cod_produto_empresa'
)
ORDER BY table_name;


-- ==========================================================================================================
-- ✅ VERIFICAÇÃO FINAL
-- ==========================================================================================================

-- Contar registros sem company_id (deverá estar vazio após reimportação do Odoo)
SELECT
    'requisicao_compras' AS tabela,
    COUNT(*) AS registros_sem_company_id
FROM requisicao_compras
WHERE company_id IS NULL

UNION ALL

SELECT
    'pedido_compras' AS tabela,
    COUNT(*) AS registros_sem_company_id
FROM pedido_compras
WHERE company_id IS NULL

UNION ALL

SELECT
    'requisicao_compra_alocacao' AS tabela,
    COUNT(*) AS registros_sem_company_id
FROM requisicao_compra_alocacao
WHERE company_id IS NULL;


-- ==========================================================================================================
-- 📋 PRÓXIMOS PASSOS
-- ==========================================================================================================

-- 1. Reimportar dados do Odoo usando os serviços atualizados
-- 2. Verificar se company_id está sendo preenchido corretamente
-- 3. Confirmar que constraints não estão bloqueando inserções válidas
