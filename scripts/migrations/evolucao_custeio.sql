-- ============================================================================
-- MIGRACAO: Sistema de Custeio - Evolucao Completa
-- Data: 2025-12-26
-- Descricao: Adiciona versionamento ao CustoConsiderado, cria tabelas auxiliares
--            e adiciona campos de snapshot/margem na CarteiraPrincipal
-- ============================================================================

-- ============================================================================
-- PARTE 1: CAMPOS DE VERSIONAMENTO EM custo_considerado
-- ============================================================================

-- 1.1 Adicionar campos de versionamento
ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS versao INTEGER DEFAULT 1;
ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS custo_atual BOOLEAN DEFAULT TRUE;
ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS vigencia_inicio TIMESTAMP DEFAULT NOW();
ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS vigencia_fim TIMESTAMP NULL;
ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS custo_producao NUMERIC(15,6) NULL;
ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS motivo_alteracao TEXT NULL;

-- 1.2 Atualizar registros existentes para ter versao = 1 e custo_atual = TRUE
UPDATE custo_considerado
SET versao = 1,
    custo_atual = TRUE,
    vigencia_inicio = COALESCE(atualizado_em, NOW())
WHERE versao IS NULL;

-- 1.3 Remover constraint unique antiga do cod_produto (se existir)
-- NOTA: A constraint pode ter diferentes nomes dependendo de como foi criada
DO $$
BEGIN
    -- Tentar remover constraint com nome padrao
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'custo_considerado_cod_produto_key') THEN
        ALTER TABLE custo_considerado DROP CONSTRAINT custo_considerado_cod_produto_key;
    END IF;
EXCEPTION
    WHEN undefined_object THEN
        NULL; -- Constraint nao existe, continuar
END $$;

-- 1.4 Criar nova constraint unique para (cod_produto, versao)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_custo_considerado_versao') THEN
        ALTER TABLE custo_considerado ADD CONSTRAINT uq_custo_considerado_versao UNIQUE (cod_produto, versao);
    END IF;
END $$;

-- 1.5 Criar indice para busca do custo atual
CREATE INDEX IF NOT EXISTS idx_custo_considerado_atual ON custo_considerado(cod_produto, custo_atual);

-- ============================================================================
-- PARTE 2: TABELA custo_frete
-- ============================================================================

CREATE TABLE IF NOT EXISTS custo_frete (
    id SERIAL PRIMARY KEY,
    incoterm VARCHAR(20) NOT NULL,
    cod_uf VARCHAR(2) NOT NULL,
    percentual_frete NUMERIC(5,2) NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE NULL,
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100),
    UNIQUE(incoterm, cod_uf, vigencia_inicio)
);

CREATE INDEX IF NOT EXISTS idx_custo_frete_vigencia ON custo_frete(incoterm, cod_uf, vigencia_inicio);

-- ============================================================================
-- PARTE 3: TABELA parametro_custeio
-- ============================================================================

CREATE TABLE IF NOT EXISTS parametro_custeio (
    id SERIAL PRIMARY KEY,
    chave VARCHAR(50) UNIQUE NOT NULL,
    valor NUMERIC(15,6) NOT NULL,
    descricao TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

-- Inserir parametro inicial de custo operacional
INSERT INTO parametro_custeio (chave, valor, descricao)
VALUES ('CUSTO_OPERACAO_PERCENTUAL', 0, 'Custo operacional percentual global aplicado a todos os produtos')
ON CONFLICT (chave) DO NOTHING;

-- ============================================================================
-- PARTE 4: CAMPOS DE SNAPSHOT E MARGEM EM carteira_principal
-- ============================================================================

-- 4.1 Campos de snapshot de custo
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_unitario_snapshot NUMERIC(15,6);
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_tipo_snapshot VARCHAR(20);
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_vigencia_snapshot TIMESTAMP;
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_producao_snapshot NUMERIC(15,6);

-- 4.2 Campos de margem calculada
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_bruta NUMERIC(15,2);
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_bruta_percentual NUMERIC(5,2);
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_liquida NUMERIC(15,2);
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_liquida_percentual NUMERIC(5,2);

-- ============================================================================
-- VERIFICACAO
-- ============================================================================

-- Verificar campos adicionados
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('custo_considerado', 'custo_frete', 'parametro_custeio', 'carteira_principal')
    AND column_name IN (
        'versao', 'custo_atual', 'vigencia_inicio', 'vigencia_fim', 'custo_producao', 'motivo_alteracao',
        'custo_unitario_snapshot', 'custo_tipo_snapshot', 'custo_vigencia_snapshot', 'custo_producao_snapshot',
        'margem_bruta', 'margem_bruta_percentual', 'margem_liquida', 'margem_liquida_percentual',
        'incoterm', 'cod_uf', 'percentual_frete', 'chave', 'valor'
    )
ORDER BY table_name, column_name;

-- ============================================================================
-- CONSULTAS UTEIS APOS MIGRACAO
-- ============================================================================

-- Custo ATUAL de um produto
-- SELECT * FROM custo_considerado WHERE cod_produto = 'XXX' AND custo_atual = TRUE;

-- Historico completo de um produto
-- SELECT * FROM custo_considerado WHERE cod_produto = 'XXX' ORDER BY versao DESC;

-- Custo frete vigente para CIF + SP
-- SELECT percentual_frete FROM custo_frete
-- WHERE incoterm = 'CIF' AND cod_uf = 'SP'
--   AND vigencia_inicio <= CURRENT_DATE
--   AND (vigencia_fim IS NULL OR vigencia_fim > CURRENT_DATE)
-- ORDER BY vigencia_inicio DESC LIMIT 1;

-- Parametro de custo operacional
-- SELECT valor FROM parametro_custeio WHERE chave = 'CUSTO_OPERACAO_PERCENTUAL';
