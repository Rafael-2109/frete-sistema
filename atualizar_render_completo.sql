-- =====================================================
-- Script COMPLETO de Atualização PostgreSQL - Render
-- Adiciona TODAS as 18 tabelas faltantes + colunas
-- =====================================================

\echo '================================================'
\echo 'ATUALIZAÇÃO COMPLETA DO BANCO PostgreSQL RENDER'
\echo '================================================'
\echo ''

-- Mostrar versão
SELECT version();

BEGIN; -- Iniciar transação

-- =====================================================
-- PARTE 1: CRIAR TABELA CADASTRO_CLIENTE (CRÍTICA!)
-- =====================================================
\echo '📌 Criando tabela CADASTRO_CLIENTE...'

CREATE TABLE IF NOT EXISTS public.cadastro_cliente (
    id SERIAL PRIMARY KEY,
    cnpj_cpf VARCHAR(20) NOT NULL UNIQUE,
    raz_social VARCHAR(255) NOT NULL,
    raz_social_red VARCHAR(100),
    municipio VARCHAR(100),
    estado VARCHAR(2),
    vendedor VARCHAR(100),
    equipe_vendas VARCHAR(100),
    cnpj_endereco_ent VARCHAR(20),
    empresa_endereco_ent VARCHAR(255),
    cep_endereco_ent VARCHAR(10),
    nome_cidade VARCHAR(100),
    cod_uf VARCHAR(2),
    bairro_endereco_ent VARCHAR(100),
    rua_endereco_ent VARCHAR(255),
    endereco_ent VARCHAR(20),
    telefone_endereco_ent VARCHAR(20),
    endereco_mesmo_cliente BOOLEAN DEFAULT true,
    cliente_ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_por VARCHAR(100),
    observacoes TEXT
);

CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_cnpj ON public.cadastro_cliente (cnpj_cpf);
CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_vendedor ON public.cadastro_cliente (vendedor);
CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_ativo ON public.cadastro_cliente (cliente_ativo);

-- =====================================================
-- PARTE 2: CRIAR TABELAS DE CACHE (CRÍTICAS!)
-- =====================================================
\echo '💾 Criando tabelas de CACHE...'

-- SALDO_ESTOQUE_CACHE
CREATE TABLE IF NOT EXISTS public.saldo_estoque_cache (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_saldo NUMERIC(15,3) DEFAULT 0,
    qtd_carteira NUMERIC(15,3) DEFAULT 0,
    qtd_disponivel NUMERIC(15,3) DEFAULT 0,
    qtd_reservada NUMERIC(15,3) DEFAULT 0,
    qtd_em_transito NUMERIC(15,3) DEFAULT 0,
    qtd_prevista NUMERIC(15,3) DEFAULT 0,
    custo_medio NUMERIC(15,2) DEFAULT 0,
    valor_total NUMERIC(15,2) DEFAULT 0,
    data_ultima_entrada DATE,
    data_ultima_saida DATE,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    versao INTEGER DEFAULT 1,
    UNIQUE(cod_produto)
);

CREATE INDEX IF NOT EXISTS idx_saldo_cache_produto ON public.saldo_estoque_cache (cod_produto);
CREATE INDEX IF NOT EXISTS idx_saldo_cache_atualizacao ON public.saldo_estoque_cache (ultima_atualizacao);

-- PROJECAO_ESTOQUE_CACHE
CREATE TABLE IF NOT EXISTS public.projecao_estoque_cache (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    data_projecao DATE NOT NULL,
    qtd_entrada_prevista NUMERIC(15,3) DEFAULT 0,
    qtd_saida_prevista NUMERIC(15,3) DEFAULT 0,
    saldo_projetado NUMERIC(15,3) DEFAULT 0,
    saldo_minimo NUMERIC(15,3) DEFAULT 0,
    ponto_reposicao NUMERIC(15,3) DEFAULT 0,
    sugestao_compra NUMERIC(15,3) DEFAULT 0,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cod_produto, data_projecao)
);

CREATE INDEX IF NOT EXISTS idx_projecao_cache_produto ON public.projecao_estoque_cache (cod_produto);
CREATE INDEX IF NOT EXISTS idx_projecao_cache_data ON public.projecao_estoque_cache (data_projecao);

-- CACHE_UPDATE_LOG
CREATE TABLE IF NOT EXISTS public.cache_update_log (
    id SERIAL PRIMARY KEY,
    tabela_cache VARCHAR(100) NOT NULL,
    tipo_atualizacao VARCHAR(50),
    registros_afetados INTEGER DEFAULT 0,
    tempo_execucao_ms INTEGER,
    mensagem TEXT,
    erro TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cache_log_tabela ON public.cache_update_log (tabela_cache);
CREATE INDEX IF NOT EXISTS idx_cache_log_criado ON public.cache_update_log (criado_em);

-- =====================================================
-- PARTE 3: CRIAR TABELAS DE PERMISSÕES FALTANTES
-- =====================================================
\echo '🔐 Criando tabelas de PERMISSÕES...'

-- BATCH_OPERATION
CREATE TABLE IF NOT EXISTS public.batch_operation (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    parameters JSONB,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- PERMISSION_LOG
CREATE TABLE IF NOT EXISTS public.permission_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100),
    resource_id INTEGER,
    old_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT true
);

-- USER_VENDEDOR
CREATE TABLE IF NOT EXISTS public.user_vendedor (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    vendedor_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_at TIMESTAMP,
    updated_by INTEGER,
    UNIQUE(user_id, vendedor_id)
);

-- USER_EQUIPE
CREATE TABLE IF NOT EXISTS public.user_equipe (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    equipe_id INTEGER NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_at TIMESTAMP,
    updated_by INTEGER,
    UNIQUE(user_id, equipe_id)
);

-- VENDEDOR_PERMISSION
CREATE TABLE IF NOT EXISTS public.vendedor_permission (
    id SERIAL PRIMARY KEY,
    vendedor_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    granted BOOLEAN DEFAULT true,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER,
    expires_at TIMESTAMP,
    notes TEXT,
    UNIQUE(vendedor_id, permission_id)
);

-- EQUIPE_PERMISSION
CREATE TABLE IF NOT EXISTS public.equipe_permission (
    id SERIAL PRIMARY KEY,
    equipe_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    granted BOOLEAN DEFAULT true,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER,
    expires_at TIMESTAMP,
    notes TEXT,
    UNIQUE(equipe_id, permission_id)
);

-- SUB_MODULE
CREATE TABLE IF NOT EXISTS public.sub_module (
    id SERIAL PRIMARY KEY,
    module_id INTEGER,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    route VARCHAR(255),
    icon VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- =====================================================
-- PARTE 4: CRIAR TABELAS MCP (OPCIONAIS)
-- =====================================================
\echo '🤖 Criando tabelas MCP...'

-- MCP_USER_PREFERENCES
CREATE TABLE IF NOT EXISTS public.mcp_user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB,
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB,
    UNIQUE(user_id, preference_key)
);

-- MCP_CONFIRMATION_REQUESTS
CREATE TABLE IF NOT EXISTS public.mcp_confirmation_requests (
    id SERIAL PRIMARY KEY,
    request_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    user_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    request_data JSONB,
    response_data JSONB,
    confirmed_at TIMESTAMP,
    confirmed_by INTEGER,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- MCP_QUERY_HISTORY
CREATE TABLE IF NOT EXISTS public.mcp_query_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50),
    parameters JSONB,
    results JSONB,
    execution_time_ms INTEGER,
    rows_affected INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    context JSONB,
    session_id VARCHAR(100),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags TEXT[],
    is_cached BOOLEAN DEFAULT false,
    cache_hit BOOLEAN DEFAULT false
);

-- MCP_ENTITY_MAPPINGS
CREATE TABLE IF NOT EXISTS public.mcp_entity_mappings (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    mapped_type VARCHAR(50) NOT NULL,
    mapped_id INTEGER NOT NULL,
    mapping_type VARCHAR(50),
    confidence_score NUMERIC(3,2),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    validated_at TIMESTAMP,
    validated_by INTEGER,
    expires_at TIMESTAMP,
    UNIQUE(entity_type, entity_id, mapped_type, mapped_id)
);

-- MCP_LEARNING_PATTERNS
CREATE TABLE IF NOT EXISTS public.mcp_learning_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_data JSONB NOT NULL,
    frequency INTEGER DEFAULT 1,
    confidence_score NUMERIC(3,2),
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSONB,
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    parent_pattern_id INTEGER,
    tags TEXT[]
);

-- MCP_ERROR_LOGS
CREATE TABLE IF NOT EXISTS public.mcp_error_logs (
    id SERIAL PRIMARY KEY,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    error_stack TEXT,
    context JSONB,
    user_id INTEGER,
    session_id VARCHAR(100),
    request_id VARCHAR(100),
    severity VARCHAR(20) DEFAULT 'error',
    is_resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP,
    resolved_by INTEGER,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- USER_PERMISSION_BACKUP (para segurança)
CREATE TABLE IF NOT EXISTS public.user_permission_backup (
    id INTEGER,
    user_id INTEGER,
    module_id INTEGER,
    submodule_id INTEGER,
    function_id INTEGER,
    permission_type VARCHAR(50),
    granted BOOLEAN,
    granted_at TIMESTAMP,
    granted_by INTEGER,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    backup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    backup_reason TEXT
);

-- =====================================================
-- PARTE 5: ADICIONAR COLUNAS FALTANTES NAS TABELAS EXISTENTES
-- =====================================================
\echo '➕ Adicionando colunas faltantes em tabelas existentes...'

-- SEPARACAO
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'separacao' 
                   AND column_name = 'separacao_lote_id') THEN
        ALTER TABLE public.separacao ADD COLUMN separacao_lote_id VARCHAR(50);
        RAISE NOTICE '✅ Coluna separacao_lote_id adicionada em separacao';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'separacao' 
                   AND column_name = 'tipo_envio') THEN
        ALTER TABLE public.separacao ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
        RAISE NOTICE '✅ Coluna tipo_envio adicionada em separacao';
    END IF;
END $$;

-- PRE_SEPARACAO_ITENS
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'pre_separacao_itens' 
                   AND column_name = 'tipo_envio') THEN
        ALTER TABLE public.pre_separacao_itens ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
        RAISE NOTICE '✅ Coluna tipo_envio adicionada em pre_separacao_itens';
    END IF;
END $$;

-- CARTEIRA_PRINCIPAL
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'carteira_principal' 
                   AND column_name = 'qtd_pre_separacoes') THEN
        ALTER TABLE public.carteira_principal ADD COLUMN qtd_pre_separacoes INTEGER DEFAULT 0;
        RAISE NOTICE '✅ Coluna qtd_pre_separacoes adicionada';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'carteira_principal' 
                   AND column_name = 'qtd_separacoes') THEN
        ALTER TABLE public.carteira_principal ADD COLUMN qtd_separacoes INTEGER DEFAULT 0;
        RAISE NOTICE '✅ Coluna qtd_separacoes adicionada';
    END IF;
END $$;

-- =====================================================
-- PARTE 6: CRIAR ÍNDICES ADICIONAIS PARA PERFORMANCE
-- =====================================================
\echo '🔍 Criando índices para melhor performance...'

CREATE INDEX IF NOT EXISTS idx_separacao_lote_id ON public.separacao (separacao_lote_id);
CREATE INDEX IF NOT EXISTS idx_separacao_num_pedido ON public.separacao (num_pedido);
CREATE INDEX IF NOT EXISTS idx_pre_separacao_carteira_id ON public.pre_separacao_itens (carteira_principal_id);
CREATE INDEX IF NOT EXISTS idx_carteira_num_pedido ON public.carteira_principal (num_pedido);
CREATE INDEX IF NOT EXISTS idx_carteira_cod_produto ON public.carteira_principal (cod_produto);
CREATE INDEX IF NOT EXISTS idx_permission_log_user ON public.permission_log (user_id);
CREATE INDEX IF NOT EXISTS idx_permission_log_created ON public.permission_log (created_at);

-- =====================================================
-- PARTE 7: LIMPEZA E INICIALIZAÇÃO
-- =====================================================
\echo '🧹 Limpando dados inválidos...'

-- Limpar separacao_lote_id inválidos
UPDATE public.separacao 
SET separacao_lote_id = NULL 
WHERE separacao_lote_id IN ('', 'null', 'NULL', 'None');

-- =====================================================
-- PARTE 8: VALIDAÇÃO FINAL
-- =====================================================
\echo '✔️ Executando validações finais...'

DO $$
DECLARE
    v_count INTEGER;
    v_table_count INTEGER;
BEGIN
    -- Contar tabelas criadas
    SELECT COUNT(*) INTO v_table_count 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('cadastro_cliente', 'saldo_estoque_cache', 'projecao_estoque_cache');
    
    RAISE NOTICE '📊 Tabelas críticas verificadas: %', v_table_count;
    
    -- Verificar cadastro_cliente
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_name = 'cadastro_cliente') THEN
        RAISE NOTICE '✅ Tabela cadastro_cliente criada com sucesso!';
    ELSE
        RAISE WARNING '⚠️ Tabela cadastro_cliente não foi criada!';
    END IF;
    
    -- Contar registros
    SELECT COUNT(*) INTO v_count FROM public.carteira_principal;
    RAISE NOTICE '📊 Total em carteira_principal: % registros', v_count;
    
    SELECT COUNT(*) INTO v_count FROM public.separacao;
    RAISE NOTICE '📊 Total em separacao: % registros', v_count;
END $$;

COMMIT; -- Confirmar todas as alterações

\echo ''
\echo '================================================'
\echo '✅ ATUALIZAÇÃO COMPLETA CONCLUÍDA!'
\echo '================================================'
\echo ''
\echo 'RESUMO DAS ALTERAÇÕES:'
\echo '  • 18 tabelas novas criadas'
\echo '  • Tabela CADASTRO_CLIENTE criada'
\echo '  • Tabelas de CACHE criadas'
\echo '  • Colunas adicionadas em tabelas existentes'
\echo '  • Índices de performance criados'
\echo ''
\echo 'Próximo passo: VACUUM ANALYZE;'

-- Para executar após o script:
-- VACUUM ANALYZE;

psql $DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_name IN ('cadastro_cliente', 'saldo_estoque_cache') ORDER BY 1;"