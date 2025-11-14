-- ============================================================================
-- Migration: Criar tabela conhecimento_transporte
-- ============================================================================
-- OBJETIVO: Criar tabela para armazenar CTes do Odoo
-- DATA: 13/11/2025
-- EXECUTAR NO: Shell do Render (psql)
-- ============================================================================

CREATE TABLE IF NOT EXISTS conhecimento_transporte (
    id SERIAL PRIMARY KEY,

    -- Vínculo Odoo
    dfe_id VARCHAR(50) NOT NULL UNIQUE,
    odoo_ativo BOOLEAN DEFAULT TRUE,
    odoo_name VARCHAR(100),
    odoo_status_codigo VARCHAR(2),
    odoo_status_descricao VARCHAR(50),

    -- Dados CTe (chave e numeração)
    chave_acesso VARCHAR(44) UNIQUE,
    numero_cte VARCHAR(20),
    serie_cte VARCHAR(10),

    -- Datas
    data_emissao DATE,
    data_entrada DATE,

    -- Valores
    valor_total NUMERIC(15, 2),
    valor_frete NUMERIC(15, 2),
    valor_icms NUMERIC(15, 2),
    vencimento DATE,

    -- Emissor (Transportadora)
    cnpj_emitente VARCHAR(20),
    nome_emitente VARCHAR(255),
    ie_emitente VARCHAR(20),

    -- Partes envolvidas
    cnpj_destinatario VARCHAR(20),
    cnpj_remetente VARCHAR(20),
    cnpj_expedidor VARCHAR(20),

    -- Municípios
    municipio_inicio VARCHAR(10),
    municipio_fim VARCHAR(10),

    -- Tomador
    tomador VARCHAR(1),

    -- Dados adicionais
    informacoes_complementares TEXT,
    tipo_pedido VARCHAR(20),

    -- Arquivos
    cte_pdf_path VARCHAR(500),
    cte_xml_path VARCHAR(500),
    cte_pdf_nome_arquivo VARCHAR(255),
    cte_xml_nome_arquivo VARCHAR(255),

    -- Relacionamentos Odoo
    odoo_partner_id INTEGER,
    odoo_invoice_ids TEXT,
    odoo_purchase_fiscal_id INTEGER,

    -- Vínculo com frete
    frete_id INTEGER REFERENCES fretes(id) ON DELETE SET NULL,
    vinculado_manualmente BOOLEAN DEFAULT FALSE,
    vinculado_em TIMESTAMP,
    vinculado_por VARCHAR(100),

    -- Auditoria
    importado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    importado_por VARCHAR(100) DEFAULT 'Sistema Odoo',
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_cte_dfe_id ON conhecimento_transporte (dfe_id);
CREATE INDEX IF NOT EXISTS idx_cte_chave_acesso ON conhecimento_transporte (chave_acesso);
CREATE INDEX IF NOT EXISTS idx_cte_numero_serie ON conhecimento_transporte (numero_cte, serie_cte);
CREATE INDEX IF NOT EXISTS idx_cte_cnpj_emitente ON conhecimento_transporte (cnpj_emitente);
CREATE INDEX IF NOT EXISTS idx_cte_cnpj_remetente ON conhecimento_transporte (cnpj_remetente);
CREATE INDEX IF NOT EXISTS idx_cte_cnpj_destinatario ON conhecimento_transporte (cnpj_destinatario);
CREATE INDEX IF NOT EXISTS idx_cte_data_emissao ON conhecimento_transporte (data_emissao);
CREATE INDEX IF NOT EXISTS idx_cte_frete ON conhecimento_transporte (frete_id);
CREATE INDEX IF NOT EXISTS idx_cte_status ON conhecimento_transporte (odoo_status_codigo);
CREATE INDEX IF NOT EXISTS idx_cte_ativo ON conhecimento_transporte (ativo);

-- Verificar criação
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
ORDER BY ordinal_position;
