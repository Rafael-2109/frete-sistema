-- =====================================================
-- Script SQL PostgreSQL para Atualização do Render
-- SEGURO: Não apaga dados, apenas adiciona estruturas
-- =====================================================
-- Para executar: psql $DATABASE_URL -f este_arquivo.sql
-- Ou copie e cole no psql interativo

\echo '================================================'
\echo 'INICIANDO ATUALIZAÇÃO DO BANCO PostgreSQL'
\echo '================================================'
\echo ''

-- Mostrar versão do PostgreSQL
SELECT version();

-- Iniciar transação
BEGIN;

\echo 'Etapa 1/6: Atualizando tabela SEPARACAO...'
-- Adicionar colunas na tabela separacao
DO $$
BEGIN
    -- Adicionar separacao_lote_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'separacao' 
        AND column_name = 'separacao_lote_id'
    ) THEN
        ALTER TABLE public.separacao ADD COLUMN separacao_lote_id VARCHAR(50);
        RAISE NOTICE '✅ Coluna separacao_lote_id adicionada';
    ELSE
        RAISE NOTICE '⏭️  Coluna separacao_lote_id já existe';
    END IF;
    
    -- Adicionar tipo_envio
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'separacao' 
        AND column_name = 'tipo_envio'
    ) THEN
        ALTER TABLE public.separacao ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
        RAISE NOTICE '✅ Coluna tipo_envio adicionada';
    ELSE
        RAISE NOTICE '⏭️  Coluna tipo_envio já existe';
    END IF;
END $$;

\echo 'Etapa 2/6: Atualizando tabela PRE_SEPARACAO_ITENS...'
-- Adicionar tipo_envio em pre_separacao_itens
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'pre_separacao_itens' 
        AND column_name = 'tipo_envio'
    ) THEN
        ALTER TABLE public.pre_separacao_itens ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
        RAISE NOTICE '✅ Coluna tipo_envio adicionada em pre_separacao_itens';
    ELSE
        RAISE NOTICE '⏭️  Coluna tipo_envio já existe em pre_separacao_itens';
    END IF;
END $$;

\echo 'Etapa 3/6: Atualizando tabela CARTEIRA_PRINCIPAL...'
-- Adicionar contadores na carteira_principal
DO $$
BEGIN
    -- qtd_pre_separacoes
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'carteira_principal' 
        AND column_name = 'qtd_pre_separacoes'
    ) THEN
        ALTER TABLE public.carteira_principal ADD COLUMN qtd_pre_separacoes INTEGER DEFAULT 0;
        RAISE NOTICE '✅ Coluna qtd_pre_separacoes adicionada';
    ELSE
        RAISE NOTICE '⏭️  Coluna qtd_pre_separacoes já existe';
    END IF;
    
    -- qtd_separacoes
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'carteira_principal' 
        AND column_name = 'qtd_separacoes'
    ) THEN
        ALTER TABLE public.carteira_principal ADD COLUMN qtd_separacoes INTEGER DEFAULT 0;
        RAISE NOTICE '✅ Coluna qtd_separacoes adicionada';
    ELSE
        RAISE NOTICE '⏭️  Coluna qtd_separacoes já existe';
    END IF;
END $$;

\echo 'Etapa 4/6: Criando índices para performance...'
-- Criar índices se não existirem
DO $$
BEGIN
    -- Índices para separacao
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_separacao_lote_id') THEN
        CREATE INDEX idx_separacao_lote_id ON public.separacao (separacao_lote_id);
        RAISE NOTICE '✅ Índice idx_separacao_lote_id criado';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_separacao_num_pedido') THEN
        CREATE INDEX idx_separacao_num_pedido ON public.separacao (num_pedido);
        RAISE NOTICE '✅ Índice idx_separacao_num_pedido criado';
    END IF;
    
    -- Índice para pre_separacao_itens
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_pre_separacao_carteira_id') THEN
        CREATE INDEX idx_pre_separacao_carteira_id ON public.pre_separacao_itens (carteira_principal_id);
        RAISE NOTICE '✅ Índice idx_pre_separacao_carteira_id criado';
    END IF;
    
    -- Índices para carteira_principal
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_carteira_num_pedido') THEN
        CREATE INDEX idx_carteira_num_pedido ON public.carteira_principal (num_pedido);
        RAISE NOTICE '✅ Índice idx_carteira_num_pedido criado';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_carteira_cod_produto') THEN
        CREATE INDEX idx_carteira_cod_produto ON public.carteira_principal (cod_produto);
        RAISE NOTICE '✅ Índice idx_carteira_cod_produto criado';
    END IF;
END $$;

\echo 'Etapa 5/6: Criando tabelas de cache...'
-- Criar tabelas de cache
CREATE TABLE IF NOT EXISTS public.saldo_estoque_cache (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_saldo NUMERIC(15,3) DEFAULT 0,
    qtd_carteira NUMERIC(15,3) DEFAULT 0,
    qtd_disponivel NUMERIC(15,3) DEFAULT 0,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cod_produto)
);

CREATE TABLE IF NOT EXISTS public.projecao_estoque_cache (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    data_projecao DATE NOT NULL,
    qtd_entrada_prevista NUMERIC(15,3) DEFAULT 0,
    qtd_saida_prevista NUMERIC(15,3) DEFAULT 0,
    saldo_projetado NUMERIC(15,3) DEFAULT 0,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cod_produto, data_projecao)
);

CREATE TABLE IF NOT EXISTS public.cache_update_log (
    id SERIAL PRIMARY KEY,
    tabela_cache VARCHAR(100) NOT NULL,
    tipo_atualizacao VARCHAR(50),
    registros_afetados INTEGER DEFAULT 0,
    tempo_execucao_ms INTEGER,
    mensagem TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices para cache
CREATE INDEX IF NOT EXISTS idx_saldo_cache_produto ON public.saldo_estoque_cache (cod_produto);
CREATE INDEX IF NOT EXISTS idx_saldo_cache_atualizacao ON public.saldo_estoque_cache (ultima_atualizacao);
CREATE INDEX IF NOT EXISTS idx_projecao_cache_produto ON public.projecao_estoque_cache (cod_produto);
CREATE INDEX IF NOT EXISTS idx_projecao_cache_data ON public.projecao_estoque_cache (data_projecao);

\echo 'Etapa 6/6: Limpando dados inválidos...'
-- Limpar valores inválidos
UPDATE public.separacao 
SET separacao_lote_id = NULL 
WHERE separacao_lote_id IN ('', 'null', 'NULL', 'None')
AND separacao_lote_id IS NOT NULL;

-- Validação final
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM public.carteira_principal;
    RAISE NOTICE '📊 Total em carteira_principal: % registros', v_count;
    
    SELECT COUNT(*) INTO v_count FROM public.separacao;
    RAISE NOTICE '📊 Total em separacao: % registros', v_count;
    
    SELECT COUNT(*) INTO v_count FROM public.pre_separacao_itens;
    RAISE NOTICE '📊 Total em pre_separacao_itens: % registros', v_count;
    
    -- Verificar se colunas críticas existem
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'separacao' AND column_name = 'separacao_lote_id'
    ) THEN
        RAISE EXCEPTION '❌ ERRO: Coluna separacao_lote_id não foi criada!';
    END IF;
    
    RAISE NOTICE '✅ Todas as validações passaram!';
END $$;

-- Confirmar transação
COMMIT;

\echo ''
\echo '================================================'
\echo '✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!'
\echo '================================================'
\echo ''
\echo 'Próximo passo: Execute VACUUM ANALYZE;'
\echo ''

-- Para executar o VACUUM, rode separadamente:
-- VACUUM ANALYZE;