-- =====================================================
-- Script SQL para criar tabela historico_requisicao_compras
-- SNAPSHOT COMPLETO: Mesmos campos da requisicao_compras
-- Para execução no Shell do Render
-- =====================================================
-- Comando: psql $DATABASE_URL < scripts/criar_tabela_historico_requisicoes.sql
-- =====================================================

-- =====================================================
-- PASSO 1: Remover tabela antiga (se existir)
-- =====================================================

-- Verificar se existe
SELECT
    CASE
        WHEN EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'historico_requisicao_compras'
        )
        THEN '⚠️  Tabela antiga encontrada - Será removida e recriada'
        ELSE 'ℹ️  Primeira criação da tabela'
    END as status;

-- Dropar tabela antiga (CASCADE remove todos os índices/constraints)
DROP TABLE IF EXISTS historico_requisicao_compras CASCADE;

SELECT '✅ Tabela antiga removida (se existia)' as resultado;

-- =====================================================
-- PASSO 2: Criar nova tabela com snapshot completo
-- =====================================================

CREATE TABLE historico_requisicao_compras (
    id SERIAL PRIMARY KEY,

    -- ================================================
    -- CAMPOS DE CONTROLE DO HISTÓRICO
    -- ================================================
    requisicao_id INTEGER NOT NULL REFERENCES requisicao_compras(id) ON DELETE CASCADE,
    operacao VARCHAR(20) NOT NULL,  -- 'CRIAR', 'EDITAR'
    alterado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alterado_por VARCHAR(100) NOT NULL,  -- 'Odoo' ou nome do usuário
    write_date_odoo TIMESTAMP,  -- Data da alteração no Odoo

    -- ================================================
    -- SNAPSHOT COMPLETO - MESMOS CAMPOS DA REQUISICAO
    -- ================================================

    -- Campos principais
    num_requisicao VARCHAR(30) NOT NULL,
    data_requisicao_criacao DATE NOT NULL,
    usuario_requisicao_criacao VARCHAR(100),
    lead_time_requisicao INTEGER,
    lead_time_previsto INTEGER,
    data_requisicao_solicitada DATE,

    -- Produto
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),

    -- Quantidades
    qtd_produto_requisicao NUMERIC(15, 3) NOT NULL,
    qtd_produto_sem_requisicao NUMERIC(15, 3) DEFAULT 0,

    -- Necessidade
    necessidade BOOLEAN DEFAULT FALSE,
    data_necessidade DATE,

    -- Status
    status VARCHAR(20) DEFAULT 'Pendente',

    -- Vínculo com Odoo
    importado_odoo BOOLEAN DEFAULT FALSE,
    odoo_id VARCHAR(50),
    requisicao_odoo_id VARCHAR(50),
    status_requisicao VARCHAR(20) DEFAULT 'rascunho',
    data_envio_odoo TIMESTAMP,
    data_confirmacao_odoo TIMESTAMP,
    observacoes_odoo TEXT,

    -- Data criação original
    criado_em TIMESTAMP
);

-- =====================================================
-- Criar índices para performance
-- =====================================================

-- Índice na requisicao_id (FK) - MAIS IMPORTANTE
CREATE INDEX IF NOT EXISTS idx_hist_req_requisicao
ON historico_requisicao_compras(requisicao_id);

-- Índice para ordenação temporal (modal)
CREATE INDEX IF NOT EXISTS idx_hist_req_requisicao_data
ON historico_requisicao_compras(requisicao_id, alterado_em DESC);

-- Índice composto: num_requisicao + data
CREATE INDEX IF NOT EXISTS idx_hist_req_num_data
ON historico_requisicao_compras(num_requisicao, alterado_em DESC);

-- Índice para busca por produto
CREATE INDEX IF NOT EXISTS idx_hist_req_produto
ON historico_requisicao_compras(cod_produto);

-- Índice para busca por operação
CREATE INDEX IF NOT EXISTS idx_hist_req_operacao
ON historico_requisicao_compras(operacao);

-- Índice para busca por quem alterou
CREATE INDEX IF NOT EXISTS idx_hist_req_alterado_por
ON historico_requisicao_compras(alterado_por);

-- =====================================================
-- Comentários nas colunas (documentação)
-- =====================================================

COMMENT ON TABLE historico_requisicao_compras IS
'Histórico completo (snapshot) de todas as alterações em Requisições de Compras. Permite comparação campo a campo entre versões.';

COMMENT ON COLUMN historico_requisicao_compras.requisicao_id IS
'ID da requisição na tabela requisicao_compras (FK)';

COMMENT ON COLUMN historico_requisicao_compras.operacao IS
'Tipo de operação: CRIAR (snapshot inicial) ou EDITAR (snapshot após alteração)';

COMMENT ON COLUMN historico_requisicao_compras.alterado_em IS
'Timestamp da alteração (para ordenação no modal)';

COMMENT ON COLUMN historico_requisicao_compras.alterado_por IS
'Origem da alteração: "Odoo" ou nome do usuário do sistema';

COMMENT ON COLUMN historico_requisicao_compras.write_date_odoo IS
'Data de alteração no Odoo (write_date) - útil para auditoria';

-- =====================================================
-- Verificar criação
-- =====================================================

-- Mostrar estrutura da tabela
\d historico_requisicao_compras

-- Mostrar índices criados
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'historico_requisicao_compras'
ORDER BY indexname;

-- Contar registros (deve ser 0 inicialmente)
SELECT COUNT(*) as total_registros FROM historico_requisicao_compras;

-- =====================================================
-- Mensagem de sucesso
-- =====================================================
SELECT '✅ Tabela historico_requisicao_compras criada com SNAPSHOT COMPLETO!' as status;
SELECT 'ℹ️  Agora você pode comparar qualquer campo entre versões no modal' as info;
