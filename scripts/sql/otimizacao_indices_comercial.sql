-- =============================================================================
-- SCRIPT DE OTIMIZAÇÃO DE ÍNDICES - MÓDULO COMERCIAL
-- =============================================================================
-- Data: 2025-01-21
-- Objetivo: Melhorar performance de consultas do módulo comercial
--
-- IMPORTANTE: Execute este script durante horário de baixo uso do sistema
-- Os índices CONCURRENTLY não bloqueiam leituras, mas podem demorar
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ÍNDICES PARA TABELA: entregas_monitoradas
-- -----------------------------------------------------------------------------
-- Problema: Consultas frequentes filtram por status_finalizacao mas não há índice
-- Evidência: cliente_service.py:270, diretoria.py:196, documento_service.py:349

-- Índice para filtros de status de finalização (mais usado no módulo comercial)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entregas_status_finalizacao
ON entregas_monitoradas (status_finalizacao);

-- Índice composto para consultas que filtram por número de NF e status
-- Usado em agregacao_service.py para JOIN com faturamento_produto
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entregas_nf_status
ON entregas_monitoradas (numero_nf, status_finalizacao);

-- Índice para consultas de entregas não finalizadas (muito comum)
-- Filtro parcial para otimizar consultas de "em aberto"
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entregas_nao_entregues
ON entregas_monitoradas (numero_nf, cnpj_cliente)
WHERE status_finalizacao IS NULL OR status_finalizacao != 'Entregue';


-- -----------------------------------------------------------------------------
-- ÍNDICES PARA TABELA: faturamento_produto
-- -----------------------------------------------------------------------------
-- Problema: Consultas agregam por equipe_vendas e filtram por status_nf

-- Índice composto para agregação por equipe com filtro de status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_equipe_status
ON faturamento_produto (equipe_vendas, status_nf);

-- Índice composto para consultas por vendedor dentro de equipe
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_equipe_vendedor
ON faturamento_produto (equipe_vendas, vendedor);

-- Índice para JOIN com entregas_monitoradas (otimiza agregacao_service.py)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_nf_equipe
ON faturamento_produto (numero_nf, equipe_vendas);


-- -----------------------------------------------------------------------------
-- ÍNDICES PARA TABELA: carteira_principal
-- -----------------------------------------------------------------------------
-- Problema: Consultas frequentes por vendedor dentro de equipe

-- Índice composto para consultas de vendedores por equipe
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_equipe_vendedor
ON carteira_principal (equipe_vendas, vendedor)
WHERE equipe_vendas IS NOT NULL AND vendedor IS NOT NULL;


-- -----------------------------------------------------------------------------
-- ÍNDICES PARA TABELA: cadastro_palletizacao
-- -----------------------------------------------------------------------------
-- Problema: LEFT JOIN frequente em produto_documento_service.py

-- Índice para otimizar JOINs por código de produto
-- NOTA: Verificar se já existe índice único em cod_produto
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_palletizacao_cod_produto
ON cadastro_palletizacao (cod_produto);


-- -----------------------------------------------------------------------------
-- VERIFICAÇÃO DE ÍNDICES CRIADOS
-- -----------------------------------------------------------------------------
-- Execute esta query para verificar se os índices foram criados:
/*
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN (
    'entregas_monitoradas',
    'faturamento_produto',
    'carteira_principal',
    'cadastro_palletizacao'
)
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
*/


-- -----------------------------------------------------------------------------
-- ANÁLISE DE ESTATÍSTICAS (RECOMENDADO APÓS CRIAR ÍNDICES)
-- -----------------------------------------------------------------------------
-- Execute ANALYZE para atualizar estatísticas do planejador de consultas:
/*
ANALYZE entregas_monitoradas;
ANALYZE faturamento_produto;
ANALYZE carteira_principal;
ANALYZE cadastro_palletizacao;
*/
