-- =============================================================================
-- FASE 1: Validacao Fiscal de Recebimento
-- =============================================================================
-- Para rodar no Shell do Render:
-- psql $DATABASE_URL < validacao_fiscal.sql
-- =============================================================================

-- 1. Tabela perfil_fiscal_produto_fornecedor
CREATE TABLE IF NOT EXISTS perfil_fiscal_produto_fornecedor (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    ncm_esperado VARCHAR(10),
    cfop_esperados TEXT,
    cst_icms_esperado VARCHAR(5),
    aliquota_icms_esperada NUMERIC(5,2),
    aliquota_icms_st_esperada NUMERIC(5,2),
    aliquota_ipi_esperada NUMERIC(5,2),
    tolerancia_bc_icms_pct NUMERIC(5,2) DEFAULT 2.0,
    tolerancia_bc_icms_st_pct NUMERIC(5,2) DEFAULT 2.0,
    tolerancia_tributos_pct NUMERIC(5,2) DEFAULT 5.0,
    ultimas_nfs_ids TEXT,
    criado_por VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,
    UNIQUE(cod_produto, cnpj_fornecedor)
);

CREATE INDEX IF NOT EXISTS idx_perfil_fiscal_produto ON perfil_fiscal_produto_fornecedor(cod_produto);
CREATE INDEX IF NOT EXISTS idx_perfil_fiscal_fornecedor ON perfil_fiscal_produto_fornecedor(cnpj_fornecedor);

-- 2. Tabela divergencia_fiscal
CREATE TABLE IF NOT EXISTS divergencia_fiscal (
    id SERIAL PRIMARY KEY,
    odoo_dfe_id VARCHAR(50) NOT NULL,
    odoo_dfe_line_id VARCHAR(50),
    perfil_fiscal_id INTEGER REFERENCES perfil_fiscal_produto_fornecedor(id) ON DELETE SET NULL,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    razao_fornecedor VARCHAR(255),
    campo VARCHAR(50) NOT NULL,
    campo_label VARCHAR(100),
    valor_esperado VARCHAR(100),
    valor_encontrado VARCHAR(100),
    diferenca_percentual NUMERIC(10,2),
    analise_ia TEXT,
    contexto_ia TEXT,
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    resolucao VARCHAR(50),
    atualizar_baseline BOOLEAN DEFAULT FALSE,
    justificativa TEXT,
    resolvido_por VARCHAR(100),
    resolvido_em TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_divergencia_dfe ON divergencia_fiscal(odoo_dfe_id);
CREATE INDEX IF NOT EXISTS idx_divergencia_status ON divergencia_fiscal(status);
CREATE INDEX IF NOT EXISTS idx_divergencia_line ON divergencia_fiscal(odoo_dfe_line_id);

-- 3. Tabela cadastro_primeira_compra
CREATE TABLE IF NOT EXISTS cadastro_primeira_compra (
    id SERIAL PRIMARY KEY,
    odoo_dfe_id VARCHAR(50) NOT NULL,
    odoo_dfe_line_id VARCHAR(50),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    razao_fornecedor VARCHAR(255),
    ncm VARCHAR(10),
    cfop VARCHAR(10),
    cst_icms VARCHAR(5),
    aliquota_icms NUMERIC(5,2),
    aliquota_icms_st NUMERIC(5,2),
    aliquota_ipi NUMERIC(5,2),
    bc_icms NUMERIC(15,2),
    bc_icms_st NUMERIC(15,2),
    valor_tributos_aprox NUMERIC(15,2),
    info_complementar TEXT,
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    validado_por VARCHAR(100),
    validado_em TIMESTAMP,
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_primeira_compra_dfe ON cadastro_primeira_compra(odoo_dfe_id);
CREATE INDEX IF NOT EXISTS idx_primeira_compra_status ON cadastro_primeira_compra(status);

-- 4. Tabela validacao_fiscal_dfe (controle do scheduler)
CREATE TABLE IF NOT EXISTS validacao_fiscal_dfe (
    id SERIAL PRIMARY KEY,
    odoo_dfe_id INTEGER NOT NULL UNIQUE,
    numero_nf VARCHAR(20),
    chave_nfe VARCHAR(44),
    cnpj_fornecedor VARCHAR(20),
    razao_fornecedor VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    total_linhas INTEGER DEFAULT 0,
    linhas_aprovadas INTEGER DEFAULT 0,
    linhas_divergentes INTEGER DEFAULT 0,
    linhas_primeira_compra INTEGER DEFAULT 0,
    erro_mensagem TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado_em TIMESTAMP,
    atualizado_em TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_validacao_dfe_odoo ON validacao_fiscal_dfe(odoo_dfe_id);
CREATE INDEX IF NOT EXISTS idx_validacao_dfe_status ON validacao_fiscal_dfe(status);
CREATE INDEX IF NOT EXISTS idx_validacao_dfe_cnpj ON validacao_fiscal_dfe(cnpj_fornecedor);
CREATE INDEX IF NOT EXISTS idx_validacao_dfe_chave ON validacao_fiscal_dfe(chave_nfe);
