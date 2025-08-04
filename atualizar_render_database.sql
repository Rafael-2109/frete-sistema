-- =====================================================
-- Script SQL de Atualização do Banco de Dados Render
-- Gerado em: 2025-08-03 22:15:21
-- =====================================================

-- IMPORTANTE: Este script contém verificações de segurança
-- Execute com cuidado e faça backup antes!

\echo 'Iniciando atualização do banco de dados...'

-- Configurações de segurança
SET statement_timeout = '30min';
SET lock_timeout = '1min';

BEGIN; -- Iniciar transação


-- Verificando e adicionando colunas na tabela separacao

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'separacao' 
        AND column_name = 'separacao_lote_id'
    ) THEN
        ALTER TABLE public.separacao ADD COLUMN separacao_lote_id VARCHAR(50);
        RAISE NOTICE 'Coluna separacao_lote_id adicionada na tabela separacao';
    ELSE
        RAISE NOTICE 'Coluna separacao_lote_id já existe na tabela separacao';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'separacao' 
        AND column_name = 'tipo_envio'
    ) THEN
        ALTER TABLE public.separacao ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
        RAISE NOTICE 'Coluna tipo_envio adicionada na tabela separacao';
    ELSE
        RAISE NOTICE 'Coluna tipo_envio já existe na tabela separacao';
    END IF;
END $$;

-- Verificando e adicionando colunas na tabela pre_separacao_itens

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'pre_separacao_itens' 
        AND column_name = 'tipo_envio'
    ) THEN
        ALTER TABLE public.pre_separacao_itens ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
        RAISE NOTICE 'Coluna tipo_envio adicionada na tabela pre_separacao_itens';
    ELSE
        RAISE NOTICE 'Coluna tipo_envio já existe na tabela pre_separacao_itens';
    END IF;
END $$;

-- Verificando e adicionando colunas na tabela carteira_principal

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'carteira_principal' 
        AND column_name = 'qtd_pre_separacoes'
    ) THEN
        ALTER TABLE public.carteira_principal ADD COLUMN qtd_pre_separacoes INTEGER DEFAULT 0;
        RAISE NOTICE 'Coluna qtd_pre_separacoes adicionada na tabela carteira_principal';
    ELSE
        RAISE NOTICE 'Coluna qtd_pre_separacoes já existe na tabela carteira_principal';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'carteira_principal' 
        AND column_name = 'qtd_separacoes'
    ) THEN
        ALTER TABLE public.carteira_principal ADD COLUMN qtd_separacoes INTEGER DEFAULT 0;
        RAISE NOTICE 'Coluna qtd_separacoes adicionada na tabela carteira_principal';
    ELSE
        RAISE NOTICE 'Coluna qtd_separacoes já existe na tabela carteira_principal';
    END IF;
END $$;


-- Criando tabela equipe_permission (se não existir)
CREATE TABLE IF NOT EXISTS public.equipe_permission (
    id INTEGER NOT NULL DEFAULT nextval('equipe_permission_id_seq'::regclass),
    equipe_id INTEGER NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    can_view BOOLEAN NOT NULL DEFAULT false,
    can_edit BOOLEAN NOT NULL DEFAULT false,
    granted_by INTEGER,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN NOT NULL DEFAULT true
,
    PRIMARY KEY (id)
);


-- Criando tabela permission_log (se não existir)
CREATE TABLE IF NOT EXISTS public.permission_log (
    id INTEGER NOT NULL DEFAULT nextval('permission_log_id_seq'::regclass),
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(20),
    entity_id INTEGER,
    details JSON,
    result VARCHAR(20),
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    session_id VARCHAR(100),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela cache_update_log (se não existir)
CREATE TABLE IF NOT EXISTS public.cache_update_log (
    id INTEGER NOT NULL DEFAULT nextval('cache_update_log_id_seq'::regclass),
    tabela_origem VARCHAR(50) NOT NULL,
    operacao VARCHAR(20) NOT NULL,
    cod_produto VARCHAR(50),
    processado BOOLEAN DEFAULT false,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela vendedor_permission (se não existir)
CREATE TABLE IF NOT EXISTS public.vendedor_permission (
    id INTEGER NOT NULL DEFAULT nextval('vendedor_permission_id_seq'::regclass),
    vendedor_id INTEGER NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    entity_id INTEGER NOT NULL,
    can_view BOOLEAN NOT NULL DEFAULT false,
    can_edit BOOLEAN NOT NULL DEFAULT false,
    granted_by INTEGER,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN NOT NULL DEFAULT true
,
    PRIMARY KEY (id)
);


-- Criando tabela mcp_entity_mappings (se não existir)
CREATE TABLE IF NOT EXISTS public.mcp_entity_mappings (
    id INTEGER NOT NULL DEFAULT nextval('mcp_entity_mappings_id_seq'::regclass),
    entity_type VARCHAR(50) NOT NULL,
    reference VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,
    entity_id VARCHAR(50),
    cnpj_root VARCHAR(8),
    variations JSON,
    entity_metadata JSON,
    confidence DOUBLE PRECISION,
    usage_count INTEGER,
    auto_detected BOOLEAN,
    verified BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_used TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela user_equipe (se não existir)
CREATE TABLE IF NOT EXISTS public.user_equipe (
    id INTEGER NOT NULL DEFAULT nextval('user_equipe_id_seq'::regclass),
    user_id INTEGER NOT NULL,
    equipe_id INTEGER NOT NULL,
    cargo_equipe VARCHAR(50),
    tipo_acesso VARCHAR(20),
    ativo BOOLEAN NOT NULL,
    adicionado_por INTEGER,
    adicionado_em TIMESTAMP NOT NULL,
    observacoes VARCHAR(255)
,
    PRIMARY KEY (id)
);


-- Criando tabela mcp_confirmation_requests (se não existir)
CREATE TABLE IF NOT EXISTS public.mcp_confirmation_requests (
    id VARCHAR(36) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    user_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    details JSON,
    status VARCHAR(20),
    created_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP,
    confirmed_by VARCHAR(100),
    rejection_reason TEXT,
    callback_data JSON
,
    PRIMARY KEY (id)
);


-- Criando tabela projecao_estoque_cache (se não existir)
CREATE TABLE IF NOT EXISTS public.projecao_estoque_cache (
    id INTEGER NOT NULL DEFAULT nextval('projecao_estoque_cache_id_seq'::regclass),
    cod_produto VARCHAR(50) NOT NULL,
    data_projecao DATE NOT NULL,
    dia_offset INTEGER NOT NULL,
    estoque_inicial NUMERIC(15, 3) NOT NULL DEFAULT 0,
    saida_prevista NUMERIC(15, 3) NOT NULL DEFAULT 0,
    producao_programada NUMERIC(15, 3) NOT NULL DEFAULT 0,
    estoque_final NUMERIC(15, 3) NOT NULL DEFAULT 0,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela user_permission_backup (se não existir)
CREATE TABLE IF NOT EXISTS public.user_permission_backup (
    id INTEGER,
    user_id INTEGER,
    entity_type VARCHAR(20),
    entity_id INTEGER,
    can_view BOOLEAN,
    can_edit BOOLEAN,
    can_delete BOOLEAN,
    can_export BOOLEAN,
    custom_override BOOLEAN,
    granted_by INTEGER,
    granted_at TIMESTAMP,
    expires_at TIMESTAMP,
    reason VARCHAR(255),
    ativo BOOLEAN
);


-- Criando tabela mcp_learning_patterns (se não existir)
CREATE TABLE IF NOT EXISTS public.mcp_learning_patterns (
    id INTEGER NOT NULL DEFAULT nextval('mcp_learning_patterns_id_seq'::regclass),
    pattern_type VARCHAR(50) NOT NULL,
    pattern_key VARCHAR(255) NOT NULL,
    pattern_value JSON NOT NULL,
    occurrence_count INTEGER,
    success_count INTEGER,
    failure_count INTEGER,
    confidence DOUBLE PRECISION,
    active BOOLEAN,
    auto_learned BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_occurred TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela mcp_error_logs (se não existir)
CREATE TABLE IF NOT EXISTS public.mcp_error_logs (
    id INTEGER NOT NULL DEFAULT nextval('mcp_error_logs_id_seq'::regclass),
    error_code VARCHAR(50) NOT NULL,
    error_category VARCHAR(50) NOT NULL,
    error_severity VARCHAR(20) NOT NULL,
    error_message TEXT NOT NULL,
    user_id INTEGER,
    query_id INTEGER,
    endpoint VARCHAR(100),
    request_data JSON,
    stack_trace TEXT,
    recovery_suggestions JSON,
    resolved BOOLEAN,
    resolution_notes TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela mcp_query_history (se não existir)
CREATE TABLE IF NOT EXISTS public.mcp_query_history (
    id INTEGER NOT NULL DEFAULT nextval('mcp_query_history_id_seq'::regclass),
    user_id INTEGER NOT NULL,
    original_query TEXT NOT NULL,
    normalized_query TEXT,
    intent VARCHAR(50),
    confidence DOUBLE PRECISION,
    entities JSON,
    context JSON,
    success BOOLEAN,
    error_code VARCHAR(50),
    error_message TEXT,
    result_count INTEGER,
    response_time_ms INTEGER,
    generated_sql TEXT,
    user_feedback VARCHAR(20),
    feedback_comment TEXT,
    created_at TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela mcp_user_preferences (se não existir)
CREATE TABLE IF NOT EXISTS public.mcp_user_preferences (
    id INTEGER NOT NULL DEFAULT nextval('mcp_user_preferences_id_seq'::regclass),
    user_id INTEGER NOT NULL,
    preference_type VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSON,
    confidence DOUBLE PRECISION,
    usage_count INTEGER,
    last_used TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela saldo_estoque_cache (se não existir)
CREATE TABLE IF NOT EXISTS public.saldo_estoque_cache (
    id INTEGER NOT NULL DEFAULT nextval('saldo_estoque_cache_id_seq'::regclass),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(200) NOT NULL,
    saldo_atual NUMERIC(15, 3) NOT NULL DEFAULT 0,
    qtd_carteira NUMERIC(15, 3) NOT NULL DEFAULT 0,
    qtd_pre_separacao NUMERIC(15, 3) NOT NULL DEFAULT 0,
    qtd_separacao NUMERIC(15, 3) NOT NULL DEFAULT 0,
    previsao_ruptura_7d NUMERIC(15, 3),
    status_ruptura VARCHAR(20),
    ultima_atualizacao_saldo TIMESTAMP,
    ultima_atualizacao_carteira TIMESTAMP,
    ultima_atualizacao_projecao TIMESTAMP,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando tabela batch_operation (se não existir)
CREATE TABLE IF NOT EXISTS public.batch_operation (
    id INTEGER NOT NULL DEFAULT nextval('batch_operation_id_seq'::regclass),
    operation_type VARCHAR(20) NOT NULL,
    description VARCHAR(255),
    executed_by INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20),
    affected_users INTEGER,
    affected_permissions INTEGER,
    details JSON,
    error_details TEXT
,
    PRIMARY KEY (id)
);


-- Criando tabela cadastro_cliente (se não existir)
CREATE TABLE IF NOT EXISTS public.cadastro_cliente (
    id INTEGER NOT NULL DEFAULT nextval('cadastro_cliente_id_seq'::regclass),
    cnpj_cpf VARCHAR(20) NOT NULL,
    raz_social VARCHAR(255) NOT NULL,
    raz_social_red VARCHAR(100),
    municipio VARCHAR(100) NOT NULL,
    estado VARCHAR(2) NOT NULL,
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
    telefone_endereco_ent VARCHAR(50),
    endereco_mesmo_cliente BOOLEAN DEFAULT true,
    cliente_ativo BOOLEAN DEFAULT true,
    criado_em TIMESTAMP NOT NULL DEFAULT now(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_por VARCHAR(100)
,
    PRIMARY KEY (id)
);


-- Criando tabela user_vendedor (se não existir)
CREATE TABLE IF NOT EXISTS public.user_vendedor (
    id INTEGER NOT NULL DEFAULT nextval('user_vendedor_id_seq'::regclass),
    user_id INTEGER NOT NULL,
    vendedor_id INTEGER NOT NULL,
    tipo_acesso VARCHAR(20),
    ativo BOOLEAN NOT NULL,
    adicionado_por INTEGER,
    adicionado_em TIMESTAMP NOT NULL,
    observacoes VARCHAR(255)
,
    PRIMARY KEY (id)
);


-- Criando tabela sub_module (se não existir)
CREATE TABLE IF NOT EXISTS public.sub_module (
    id INTEGER NOT NULL DEFAULT nextval('sub_module_id_seq'::regclass),
    modulo_id INTEGER NOT NULL,
    nome VARCHAR(50) NOT NULL,
    nome_exibicao VARCHAR(100) NOT NULL,
    descricao VARCHAR(255),
    icone VARCHAR(50),
    ativo BOOLEAN NOT NULL DEFAULT true,
    ordem INTEGER NOT NULL DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
,
    PRIMARY KEY (id)
);


-- Criando índices para performance

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'separacao' 
        AND indexname = 'idx_separacao_lote_id'
    ) THEN
        CREATE INDEX idx_separacao_lote_id ON public.separacao (separacao_lote_id);
        RAISE NOTICE 'Índice idx_separacao_lote_id criado na tabela separacao';
    ELSE
        RAISE NOTICE 'Índice idx_separacao_lote_id já existe na tabela separacao';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'separacao' 
        AND indexname = 'idx_separacao_num_pedido'
    ) THEN
        CREATE INDEX idx_separacao_num_pedido ON public.separacao (num_pedido);
        RAISE NOTICE 'Índice idx_separacao_num_pedido criado na tabela separacao';
    ELSE
        RAISE NOTICE 'Índice idx_separacao_num_pedido já existe na tabela separacao';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'pre_separacao_itens' 
        AND indexname = 'idx_pre_separacao_carteira_id'
    ) THEN
        CREATE INDEX idx_pre_separacao_carteira_id ON public.pre_separacao_itens (carteira_principal_id);
        RAISE NOTICE 'Índice idx_pre_separacao_carteira_id criado na tabela pre_separacao_itens';
    ELSE
        RAISE NOTICE 'Índice idx_pre_separacao_carteira_id já existe na tabela pre_separacao_itens';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'carteira_principal' 
        AND indexname = 'idx_carteira_num_pedido'
    ) THEN
        CREATE INDEX idx_carteira_num_pedido ON public.carteira_principal (num_pedido);
        RAISE NOTICE 'Índice idx_carteira_num_pedido criado na tabela carteira_principal';
    ELSE
        RAISE NOTICE 'Índice idx_carteira_num_pedido já existe na tabela carteira_principal';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'carteira_principal' 
        AND indexname = 'idx_carteira_cod_produto'
    ) THEN
        CREATE INDEX idx_carteira_cod_produto ON public.carteira_principal (cod_produto);
        RAISE NOTICE 'Índice idx_carteira_cod_produto criado na tabela carteira_principal';
    ELSE
        RAISE NOTICE 'Índice idx_carteira_cod_produto já existe na tabela carteira_principal';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'vinculacao_carteira_separacao' 
        AND indexname = 'idx_vinculacao_lote'
    ) THEN
        CREATE INDEX idx_vinculacao_lote ON public.vinculacao_carteira_separacao (separacao_lote_id);
        RAISE NOTICE 'Índice idx_vinculacao_lote criado na tabela vinculacao_carteira_separacao';
    ELSE
        RAISE NOTICE 'Índice idx_vinculacao_lote já existe na tabela vinculacao_carteira_separacao';
    END IF;
END $$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'vinculacao_carteira_separacao' 
        AND indexname = 'idx_vinculacao_pedido'
    ) THEN
        CREATE INDEX idx_vinculacao_pedido ON public.vinculacao_carteira_separacao (num_pedido);
        RAISE NOTICE 'Índice idx_vinculacao_pedido criado na tabela vinculacao_carteira_separacao';
    ELSE
        RAISE NOTICE 'Índice idx_vinculacao_pedido já existe na tabela vinculacao_carteira_separacao';
    END IF;
END $$;


-- Ajustando sequences

DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Verificar se a tabela existe
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'carteira_principal') THEN
        -- Obter o máximo ID da tabela
        EXECUTE 'SELECT COALESCE(MAX(id), 0) FROM public.carteira_principal' INTO max_id;
        
        -- Ajustar a sequence se existir
        IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'carteira_principal_id_seq') THEN
            PERFORM setval('public.carteira_principal_id_seq', max_id + 1, false);
            RAISE NOTICE 'Sequence carteira_principal_id_seq ajustada para %', max_id + 1;
        END IF;
    END IF;
END $$;


DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Verificar se a tabela existe
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'separacao') THEN
        -- Obter o máximo ID da tabela
        EXECUTE 'SELECT COALESCE(MAX(id), 0) FROM public.separacao' INTO max_id;
        
        -- Ajustar a sequence se existir
        IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'separacao_id_seq') THEN
            PERFORM setval('public.separacao_id_seq', max_id + 1, false);
            RAISE NOTICE 'Sequence separacao_id_seq ajustada para %', max_id + 1;
        END IF;
    END IF;
END $$;


DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Verificar se a tabela existe
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pre_separacao_itens') THEN
        -- Obter o máximo ID da tabela
        EXECUTE 'SELECT COALESCE(MAX(id), 0) FROM public.pre_separacao_itens' INTO max_id;
        
        -- Ajustar a sequence se existir
        IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'pre_separacao_itens_id_seq') THEN
            PERFORM setval('public.pre_separacao_itens_id_seq', max_id + 1, false);
            RAISE NOTICE 'Sequence pre_separacao_itens_id_seq ajustada para %', max_id + 1;
        END IF;
    END IF;
END $$;


DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Verificar se a tabela existe
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vinculacao_carteira_separacao') THEN
        -- Obter o máximo ID da tabela
        EXECUTE 'SELECT COALESCE(MAX(id), 0) FROM public.vinculacao_carteira_separacao' INTO max_id;
        
        -- Ajustar a sequence se existir
        IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'vinculacao_carteira_separacao_id_seq') THEN
            PERFORM setval('public.vinculacao_carteira_separacao_id_seq', max_id + 1, false);
            RAISE NOTICE 'Sequence vinculacao_carteira_separacao_id_seq ajustada para %', max_id + 1;
        END IF;
    END IF;
END $$;


-- Limpeza de dados órfãos
\echo 'Limpando dados órfãos...'

-- Remover pré-separações sem carteira correspondente
DELETE FROM public.pre_separacao_itens psi
WHERE NOT EXISTS (
    SELECT 1 FROM public.carteira_principal cp 
    WHERE cp.id = psi.carteira_principal_id
);

-- Remover separações com lote_id inválido
UPDATE public.separacao 
SET separacao_lote_id = NULL 
WHERE separacao_lote_id = '' OR separacao_lote_id = 'null';



-- Validações finais
\echo 'Executando validações...'

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Verificar integridade das tabelas principais
    SELECT COUNT(*) INTO v_count FROM public.carteira_principal;
    RAISE NOTICE 'Registros em carteira_principal: %', v_count;
    
    SELECT COUNT(*) INTO v_count FROM public.separacao;
    RAISE NOTICE 'Registros em separacao: %', v_count;
    
    SELECT COUNT(*) INTO v_count FROM public.pre_separacao_itens;
    RAISE NOTICE 'Registros em pre_separacao_itens: %', v_count;
    
    -- Verificar colunas críticas
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'separacao' AND column_name = 'separacao_lote_id'
    ) THEN
        RAISE EXCEPTION 'ERRO: Coluna separacao_lote_id não foi criada!';
    END IF;
END $$;

COMMIT; -- Confirmar transação

\echo 'Atualização concluída com sucesso!'
\echo 'IMPORTANTE: Execute VACUUM ANALYZE após este script!'
