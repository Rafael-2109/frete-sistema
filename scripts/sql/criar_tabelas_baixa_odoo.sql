-- ============================================================================
-- CRIAÇÃO DAS TABELAS DE BAIXA/RECONCILIAÇÃO DO ODOO
--
-- Tabelas:
-- 1. contas_a_receber_reconciliacao - Espelha account.partial.reconcile
-- 2. contas_a_receber_pagamento - Espelha account.payment
-- 3. contas_a_receber_documento - Espelha account.move
-- 4. contas_a_receber_linha_credito - Espelha account.move.line (créditos)
--
-- Para executar no Render Shell:
-- psql $DATABASE_URL -f criar_tabelas_baixa_odoo.sql
--
-- Data: 2025-11-28
-- ============================================================================

-- ============================================================================
-- 1. TABELA: contas_a_receber_reconciliacao
-- Espelha account.partial.reconcile do Odoo
-- ============================================================================

CREATE TABLE IF NOT EXISTS contas_a_receber_reconciliacao (
    id SERIAL PRIMARY KEY,

    -- FK para ContasAReceber (título)
    conta_a_receber_id INTEGER NOT NULL REFERENCES contas_a_receber(id),

    -- Campos do Odoo (account.partial.reconcile)
    odoo_id INTEGER NOT NULL UNIQUE,
    amount FLOAT,
    debit_move_id INTEGER,
    credit_move_id INTEGER,
    debit_amount_currency FLOAT,
    credit_amount_currency FLOAT,
    debit_currency VARCHAR(10),
    credit_currency VARCHAR(10),
    full_reconcile_id INTEGER,
    exchange_move_id INTEGER,
    max_date DATE,
    company_id INTEGER,
    company_name VARCHAR(100),

    -- Auditoria Odoo
    odoo_create_date TIMESTAMP,
    odoo_create_uid INTEGER,
    odoo_create_user VARCHAR(100),
    odoo_write_date TIMESTAMP,
    odoo_write_uid INTEGER,
    odoo_write_user VARCHAR(100),

    -- Campos enriquecidos
    tipo_baixa VARCHAR(50),
    tipo_baixa_odoo VARCHAR(20),
    credit_move_name VARCHAR(255),
    credit_move_ref VARCHAR(255),
    payment_id INTEGER,
    documento_id INTEGER,

    -- Controle local
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_sincronizacao TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_reconciliacao_odoo_id ON contas_a_receber_reconciliacao(odoo_id);
CREATE INDEX IF NOT EXISTS idx_reconciliacao_conta ON contas_a_receber_reconciliacao(conta_a_receber_id);
CREATE INDEX IF NOT EXISTS idx_reconciliacao_payment ON contas_a_receber_reconciliacao(payment_id);
CREATE INDEX IF NOT EXISTS idx_reconciliacao_full ON contas_a_receber_reconciliacao(full_reconcile_id);

-- ============================================================================
-- 2. TABELA: contas_a_receber_pagamento
-- Espelha account.payment do Odoo
-- ============================================================================

CREATE TABLE IF NOT EXISTS contas_a_receber_pagamento (
    id SERIAL PRIMARY KEY,

    -- Identificação
    odoo_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(100),
    ref VARCHAR(255),

    -- Tipo e direção
    payment_type VARCHAR(20),
    partner_type VARCHAR(20),

    -- Valores
    amount FLOAT,
    currency VARCHAR(10),

    -- Datas e status
    date DATE,
    state VARCHAR(20),

    -- Relacionamentos no Odoo
    move_id INTEGER,
    partner_id INTEGER,
    partner_name VARCHAR(255),
    partner_cnpj VARCHAR(20),
    journal_id INTEGER,
    journal_name VARCHAR(100),
    reconciled_invoice_ids TEXT,
    reconciled_invoices_count INTEGER,

    -- Método de pagamento
    payment_method_line_id INTEGER,
    payment_method_code VARCHAR(50),
    payment_method_name VARCHAR(100),

    -- Empresa
    company_id INTEGER,
    company_name VARCHAR(100),

    -- Auditoria Odoo
    odoo_create_date TIMESTAMP,
    odoo_create_user VARCHAR(100),
    odoo_write_date TIMESTAMP,
    odoo_write_user VARCHAR(100),

    -- Controle local
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_sincronizacao TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_pagamento_odoo_id ON contas_a_receber_pagamento(odoo_id);
CREATE INDEX IF NOT EXISTS idx_pagamento_partner ON contas_a_receber_pagamento(partner_id);
CREATE INDEX IF NOT EXISTS idx_pagamento_date ON contas_a_receber_pagamento(date);

-- ============================================================================
-- 3. TABELA: contas_a_receber_documento
-- Espelha account.move do Odoo (notas de crédito, ajustes)
-- ============================================================================

CREATE TABLE IF NOT EXISTS contas_a_receber_documento (
    id SERIAL PRIMARY KEY,

    -- Identificação
    odoo_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(100),
    ref VARCHAR(255),

    -- Tipo do documento
    move_type VARCHAR(20),

    -- Status
    state VARCHAR(20),
    payment_state VARCHAR(20),

    -- Valores
    amount_total FLOAT,
    amount_residual FLOAT,
    amount_untaxed FLOAT,
    amount_tax FLOAT,
    currency VARCHAR(10),

    -- Datas
    date DATE,
    invoice_date DATE,

    -- Cliente/Parceiro
    partner_id INTEGER,
    partner_name VARCHAR(255),
    partner_cnpj VARCHAR(20),

    -- Relacionamentos no Odoo
    reversed_entry_id INTEGER,
    reversal_move_ids TEXT,
    payment_id INTEGER,
    journal_id INTEGER,
    journal_name VARCHAR(100),

    -- Empresa
    company_id INTEGER,
    company_name VARCHAR(100),

    -- Origem
    invoice_origin VARCHAR(255),

    -- Auditoria Odoo
    odoo_create_date TIMESTAMP,
    odoo_create_user VARCHAR(100),
    odoo_write_date TIMESTAMP,
    odoo_write_user VARCHAR(100),

    -- Controle local
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_sincronizacao TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_documento_odoo_id ON contas_a_receber_documento(odoo_id);
CREATE INDEX IF NOT EXISTS idx_documento_move_type ON contas_a_receber_documento(move_type);
CREATE INDEX IF NOT EXISTS idx_documento_partner ON contas_a_receber_documento(partner_id);

-- ============================================================================
-- 4. TABELA: contas_a_receber_linha_credito
-- Espelha account.move.line do Odoo (linhas de crédito)
-- ============================================================================

CREATE TABLE IF NOT EXISTS contas_a_receber_linha_credito (
    id SERIAL PRIMARY KEY,

    -- Identificação
    odoo_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(255),
    ref VARCHAR(255),

    -- Documento pai
    move_id INTEGER,
    move_name VARCHAR(100),
    move_type VARCHAR(20),

    -- Valores
    balance FLOAT,
    debit FLOAT,
    credit FLOAT,
    amount_currency FLOAT,
    amount_residual FLOAT,
    currency VARCHAR(10),

    -- Datas
    date DATE,
    date_maturity DATE,

    -- Conta contábil
    account_id INTEGER,
    account_name VARCHAR(255),
    account_type VARCHAR(50),

    -- Cliente
    partner_id INTEGER,
    partner_name VARCHAR(255),

    -- Vínculo com pagamento
    payment_id INTEGER,

    -- Reconciliação
    reconciled BOOLEAN DEFAULT FALSE,
    full_reconcile_id INTEGER,
    matching_number VARCHAR(50),

    -- Diário
    journal_id INTEGER,
    journal_name VARCHAR(100),

    -- Empresa
    company_id INTEGER,
    company_name VARCHAR(100),

    -- Status
    parent_state VARCHAR(20),

    -- Auditoria Odoo
    odoo_create_date TIMESTAMP,
    odoo_write_date TIMESTAMP,

    -- Controle local
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_sincronizacao TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_linha_credito_odoo_id ON contas_a_receber_linha_credito(odoo_id);
CREATE INDEX IF NOT EXISTS idx_linha_credito_move ON contas_a_receber_linha_credito(move_id);
CREATE INDEX IF NOT EXISTS idx_linha_credito_payment ON contas_a_receber_linha_credito(payment_id);

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

SELECT 'Tabelas criadas:' AS info;
SELECT table_name,
       (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = t.table_name) as colunas
FROM information_schema.tables t
WHERE table_name IN (
    'contas_a_receber_reconciliacao',
    'contas_a_receber_pagamento',
    'contas_a_receber_documento',
    'contas_a_receber_linha_credito'
)
ORDER BY table_name;
