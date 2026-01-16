-- =====================================================
-- FASE 2: Vinculacao NF x PO - Recebimento de Materiais
-- Data: 15/01/2026
-- Descricao: Tabelas para validacao e match de NF com PO
-- =====================================================

-- 1. De-Para Produto/Fornecedor
-- Converte codigo do fornecedor para codigo interno
CREATE TABLE IF NOT EXISTS produto_fornecedor_depara (
    id SERIAL PRIMARY KEY,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    razao_fornecedor VARCHAR(255),
    cod_produto_fornecedor VARCHAR(50) NOT NULL,
    descricao_produto_fornecedor VARCHAR(255),
    cod_produto_interno VARCHAR(50) NOT NULL,
    nome_produto_interno VARCHAR(255),
    odoo_product_id INTEGER,
    um_fornecedor VARCHAR(20),                      -- det_prod_ucom (ML, MI, MIL, etc.)
    um_interna VARCHAR(20) DEFAULT 'UNITS',         -- product_uom
    fator_conversao NUMERIC(10,4) DEFAULT 1.0000,   -- 1000 para Milhar
    ativo BOOLEAN DEFAULT TRUE,
    sincronizado_odoo BOOLEAN DEFAULT FALSE,
    odoo_supplierinfo_id INTEGER,
    criado_por VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    UNIQUE(cnpj_fornecedor, cod_produto_fornecedor)
);

-- 2. Resultado de Match NF x PO (por item da NF)
-- Registra o resultado do match de cada item da NF
CREATE TABLE IF NOT EXISTS match_nf_po_item (
    id SERIAL PRIMARY KEY,
    validacao_id INTEGER NOT NULL,              -- FK para validacao_nf_po_dfe
    odoo_dfe_line_id INTEGER NOT NULL,          -- Linha da NF
    cod_produto_fornecedor VARCHAR(50),         -- Codigo na NF (det_prod_cprod)
    cod_produto_interno VARCHAR(50),            -- Codigo convertido (default_code)
    nome_produto VARCHAR(255),
    qtd_nf NUMERIC(15,3),                       -- Quantidade na NF
    preco_nf NUMERIC(15,4),                     -- Preco na NF (apos conversao UM)
    data_nf DATE,                               -- Data da NF
    um_nf VARCHAR(20),                          -- Unidade de medida na NF
    fator_conversao NUMERIC(10,4),              -- Fator usado na conversao
    -- PO Match encontrado (null se nao encontrou)
    odoo_po_id INTEGER,
    odoo_po_name VARCHAR(50),
    odoo_po_line_id INTEGER,
    qtd_po NUMERIC(15,3),
    preco_po NUMERIC(15,4),
    data_po DATE,
    -- Status do match
    status_match VARCHAR(20) NOT NULL,          -- match, sem_depara, sem_po, preco_diverge, data_diverge, qtd_diverge
    motivo_bloqueio TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Divergencias/Pendencias NF x PO (quando NAO faz match 100%)
-- Registra divergencias para resolucao manual
CREATE TABLE IF NOT EXISTS divergencia_nf_po (
    id SERIAL PRIMARY KEY,
    validacao_id INTEGER NOT NULL,              -- FK para validacao_nf_po_dfe
    odoo_dfe_id INTEGER NOT NULL,
    odoo_dfe_line_id INTEGER,
    cnpj_fornecedor VARCHAR(20),
    razao_fornecedor VARCHAR(255),
    cod_produto_fornecedor VARCHAR(50),
    cod_produto_interno VARCHAR(50),
    nome_produto VARCHAR(255),
    tipo_divergencia VARCHAR(50) NOT NULL,      -- sem_depara, sem_po, preco, quantidade, data_entrega
    campo_label VARCHAR(100),
    valor_nf VARCHAR(100),
    valor_po VARCHAR(100),
    diferenca_percentual NUMERIC(10,2),
    -- PO candidato (se houver)
    odoo_po_id INTEGER,
    odoo_po_name VARCHAR(50),
    odoo_po_line_id INTEGER,
    -- Resolucao
    status VARCHAR(20) DEFAULT 'pendente',      -- pendente, aprovada, rejeitada
    resolucao VARCHAR(50),                      -- aprovar_preco, criar_depara, rejeitar, ajustar_po
    justificativa TEXT,
    resolvido_por VARCHAR(100),
    resolvido_em TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Controle de Validacao NF x PO por DFE
-- Status geral da validacao de cada NF
CREATE TABLE IF NOT EXISTS validacao_nf_po_dfe (
    id SERIAL PRIMARY KEY,
    odoo_dfe_id INTEGER NOT NULL UNIQUE,
    numero_nf VARCHAR(20),
    serie_nf VARCHAR(10),
    chave_nfe VARCHAR(44),
    cnpj_fornecedor VARCHAR(20),
    razao_fornecedor VARCHAR(255),
    data_nf DATE,
    valor_total_nf NUMERIC(15,2),
    status VARCHAR(20) DEFAULT 'pendente',      -- pendente, validando, aprovado, bloqueado, consolidado, erro
    -- Contadores
    total_itens INTEGER DEFAULT 0,
    itens_match INTEGER DEFAULT 0,
    itens_sem_depara INTEGER DEFAULT 0,
    itens_sem_po INTEGER DEFAULT 0,
    itens_preco_diverge INTEGER DEFAULT 0,
    itens_data_diverge INTEGER DEFAULT 0,
    itens_qtd_diverge INTEGER DEFAULT 0,
    -- Resultado da consolidacao (se aprovado)
    po_consolidado_id INTEGER,                  -- PO principal apos consolidacao
    po_consolidado_name VARCHAR(50),
    pos_saldo_ids TEXT,                         -- JSON: [{"id": 123, "name": "PO00456"}, ...]
    pos_cancelados_ids TEXT,                    -- JSON: [{"id": 124, "name": "PO00457"}, ...]
    acao_executada JSONB,                       -- Detalhes completos da acao
    -- Controle
    erro_mensagem TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado_em TIMESTAMP,
    consolidado_em TIMESTAMP,
    atualizado_em TIMESTAMP
);

-- =====================================================
-- INDICES
-- =====================================================

-- De-Para
CREATE INDEX IF NOT EXISTS idx_depara_cnpj ON produto_fornecedor_depara(cnpj_fornecedor);
CREATE INDEX IF NOT EXISTS idx_depara_cod_forn ON produto_fornecedor_depara(cod_produto_fornecedor);
CREATE INDEX IF NOT EXISTS idx_depara_cod_interno ON produto_fornecedor_depara(cod_produto_interno);
CREATE INDEX IF NOT EXISTS idx_depara_ativo ON produto_fornecedor_depara(ativo);

-- Match Item
CREATE INDEX IF NOT EXISTS idx_match_validacao ON match_nf_po_item(validacao_id);
CREATE INDEX IF NOT EXISTS idx_match_status ON match_nf_po_item(status_match);
CREATE INDEX IF NOT EXISTS idx_match_dfe_line ON match_nf_po_item(odoo_dfe_line_id);

-- Divergencia
CREATE INDEX IF NOT EXISTS idx_div_nf_po_validacao ON divergencia_nf_po(validacao_id);
CREATE INDEX IF NOT EXISTS idx_div_nf_po_status ON divergencia_nf_po(status);
CREATE INDEX IF NOT EXISTS idx_div_nf_po_tipo ON divergencia_nf_po(tipo_divergencia);
CREATE INDEX IF NOT EXISTS idx_div_nf_po_dfe ON divergencia_nf_po(odoo_dfe_id);

-- Validacao DFE
CREATE INDEX IF NOT EXISTS idx_val_nf_po_status ON validacao_nf_po_dfe(status);
CREATE INDEX IF NOT EXISTS idx_val_nf_po_dfe ON validacao_nf_po_dfe(odoo_dfe_id);
CREATE INDEX IF NOT EXISTS idx_val_nf_po_cnpj ON validacao_nf_po_dfe(cnpj_fornecedor);
CREATE INDEX IF NOT EXISTS idx_val_nf_po_data ON validacao_nf_po_dfe(data_nf);

-- =====================================================
-- FOREIGN KEYS
-- =====================================================

ALTER TABLE match_nf_po_item
    ADD CONSTRAINT fk_match_validacao
    FOREIGN KEY (validacao_id)
    REFERENCES validacao_nf_po_dfe(id)
    ON DELETE CASCADE;

ALTER TABLE divergencia_nf_po
    ADD CONSTRAINT fk_div_validacao
    FOREIGN KEY (validacao_id)
    REFERENCES validacao_nf_po_dfe(id)
    ON DELETE CASCADE;

-- =====================================================
-- COMENTARIOS
-- =====================================================

COMMENT ON TABLE produto_fornecedor_depara IS 'De-Para de produtos: converte codigo do fornecedor para codigo interno';
COMMENT ON TABLE match_nf_po_item IS 'Resultado do match de cada item da NF com PO';
COMMENT ON TABLE divergencia_nf_po IS 'Divergencias NF x PO para resolucao manual';
COMMENT ON TABLE validacao_nf_po_dfe IS 'Controle de status de validacao NF x PO por DFE';

COMMENT ON COLUMN produto_fornecedor_depara.fator_conversao IS 'Fator de conversao de UM. Ex: 1000 para Milhar (1 ML = 1000 units)';
COMMENT ON COLUMN validacao_nf_po_dfe.status IS 'pendente=aguardando, validando=em processo, aprovado=100% match, bloqueado=divergencias, consolidado=POs ajustados, erro=falha';
COMMENT ON COLUMN match_nf_po_item.status_match IS 'match=OK, sem_depara=sem conversao, sem_po=sem pedido, preco_diverge=preco diferente, data_diverge=fora prazo, qtd_diverge=qtd excede 10%';
