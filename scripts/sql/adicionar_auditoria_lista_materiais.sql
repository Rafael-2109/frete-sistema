-- ============================================================================
-- MIGRATION: Adicionar Auditoria em Lista de Materiais
-- Data: 2025-01-28
-- Descrição: Adiciona campos de auditoria e cria tabela de histórico
-- ============================================================================
-- IMPORTANTE: Execute no Shell do Render.com (PostgreSQL)
-- ============================================================================

BEGIN;

-- ============================================================================
-- ETAPA 1: Adicionar campos de auditoria em lista_materiais
-- ============================================================================

-- Verificar se campos já existem antes de adicionar
DO $$
BEGIN
    -- atualizado_em
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'lista_materiais' AND column_name = 'atualizado_em'
    ) THEN
        ALTER TABLE lista_materiais ADD COLUMN atualizado_em TIMESTAMP;
        RAISE NOTICE '✅ Campo atualizado_em adicionado';
    ELSE
        RAISE NOTICE '⏭️  Campo atualizado_em já existe';
    END IF;

    -- atualizado_por
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'lista_materiais' AND column_name = 'atualizado_por'
    ) THEN
        ALTER TABLE lista_materiais ADD COLUMN atualizado_por VARCHAR(100);
        RAISE NOTICE '✅ Campo atualizado_por adicionado';
    ELSE
        RAISE NOTICE '⏭️  Campo atualizado_por já existe';
    END IF;

    -- inativado_em
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'lista_materiais' AND column_name = 'inativado_em'
    ) THEN
        ALTER TABLE lista_materiais ADD COLUMN inativado_em TIMESTAMP;
        RAISE NOTICE '✅ Campo inativado_em adicionado';
    ELSE
        RAISE NOTICE '⏭️  Campo inativado_em já existe';
    END IF;

    -- inativado_por
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'lista_materiais' AND column_name = 'inativado_por'
    ) THEN
        ALTER TABLE lista_materiais ADD COLUMN inativado_por VARCHAR(100);
        RAISE NOTICE '✅ Campo inativado_por adicionado';
    ELSE
        RAISE NOTICE '⏭️  Campo inativado_por já existe';
    END IF;

    -- motivo_inativacao
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'lista_materiais' AND column_name = 'motivo_inativacao'
    ) THEN
        ALTER TABLE lista_materiais ADD COLUMN motivo_inativacao TEXT;
        RAISE NOTICE '✅ Campo motivo_inativacao adicionado';
    ELSE
        RAISE NOTICE '⏭️  Campo motivo_inativacao já existe';
    END IF;

    RAISE NOTICE '✅ Etapa 1: Campos de auditoria processados!';
END $$;

-- Adicionar default em versao
ALTER TABLE lista_materiais ALTER COLUMN versao SET DEFAULT 'v1';

-- Atualizar registros sem versão
UPDATE lista_materiais
SET versao = 'v1'
WHERE versao IS NULL OR versao = '';


-- ============================================================================
-- ETAPA 2: Criar tabela lista_materiais_historico
-- ============================================================================

CREATE TABLE IF NOT EXISTS lista_materiais_historico (
    id SERIAL PRIMARY KEY,

    -- Referência ao registro original
    lista_materiais_id INTEGER NOT NULL,

    -- Tipo de operação
    operacao VARCHAR(20) NOT NULL,

    -- Snapshot dos dados no momento da alteração
    cod_produto_produzido VARCHAR(50) NOT NULL,
    nome_produto_produzido VARCHAR(255),
    cod_produto_componente VARCHAR(50) NOT NULL,
    nome_produto_componente VARCHAR(255),
    versao VARCHAR(100),

    -- Valores ANTES da alteração (null para operação CRIAR)
    qtd_utilizada_antes NUMERIC(15, 6),
    status_antes VARCHAR(10),

    -- Valores DEPOIS da alteração
    qtd_utilizada_depois NUMERIC(15, 6),
    status_depois VARCHAR(10),

    -- Metadados da alteração
    alterado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    alterado_por VARCHAR(100) NOT NULL,
    motivo TEXT,

    -- Dados adicionais flexíveis (JSON)
    dados_adicionais JSONB
);

DO $$
BEGIN
    RAISE NOTICE '✅ Etapa 2: Tabela lista_materiais_historico criada!';
END $$;


-- ============================================================================
-- ETAPA 3: Criar índices para performance
-- ============================================================================

-- Índices em lista_materiais
CREATE INDEX IF NOT EXISTS idx_lista_materiais_status_data
    ON lista_materiais(status, criado_em);

-- Índices em lista_materiais_historico
CREATE INDEX IF NOT EXISTS idx_historico_lista_materiais_id
    ON lista_materiais_historico(lista_materiais_id);

CREATE INDEX IF NOT EXISTS idx_historico_produto_data
    ON lista_materiais_historico(cod_produto_produzido, alterado_em);

CREATE INDEX IF NOT EXISTS idx_historico_componente_data
    ON lista_materiais_historico(cod_produto_componente, alterado_em);

CREATE INDEX IF NOT EXISTS idx_historico_operacao_data
    ON lista_materiais_historico(operacao, alterado_em);

CREATE INDEX IF NOT EXISTS idx_historico_alterado_por
    ON lista_materiais_historico(alterado_por);

DO $$
BEGIN
    RAISE NOTICE '✅ Etapa 3: Índices de performance criados!';
END $$;


-- ============================================================================
-- ETAPA 4: Verificação final
-- ============================================================================

DO $$
DECLARE
    count_lista INTEGER;
    count_historico INTEGER;
BEGIN
    SELECT COUNT(*) INTO count_lista FROM lista_materiais;
    SELECT COUNT(*) INTO count_historico FROM lista_materiais_historico;

    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '📊 Total de registros em lista_materiais: %', count_lista;
    RAISE NOTICE '📊 Total de registros em lista_materiais_historico: %', count_historico;
    RAISE NOTICE '============================================================================';
END $$;

COMMIT;

-- ============================================================================
-- FIM DA MIGRATION
-- ============================================================================
