-- ============================================================
-- Criar tabela contas_a_receber_reconciliacao
-- Executar no Render (PostgreSQL)
-- Data: 2025-11-28
-- ============================================================

CREATE TABLE IF NOT EXISTS contas_a_receber_reconciliacao (
    id SERIAL PRIMARY KEY,

    -- FK para ContasAReceber
    conta_a_receber_id INTEGER NOT NULL REFERENCES contas_a_receber(id),

    -- Identificação Odoo
    odoo_id INTEGER NOT NULL UNIQUE,

    -- Valor e Data
    amount FLOAT,
    max_date DATE,

    -- Classificação do Tipo de Baixa
    tipo_baixa VARCHAR(50),
    tipo_baixa_odoo VARCHAR(20),
    payment_odoo_id INTEGER,
    journal_code VARCHAR(20),

    -- Referência Visual
    credit_move_name VARCHAR(255),
    credit_move_ref VARCHAR(255),

    -- Identificadores Odoo
    credit_move_id INTEGER,
    debit_move_id INTEGER,

    -- Empresa
    company_id INTEGER,

    -- Auditoria Odoo
    odoo_create_date TIMESTAMP,
    odoo_write_date TIMESTAMP,

    -- Controle Local
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_sincronizacao TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_reconciliacao_odoo_id ON contas_a_receber_reconciliacao(odoo_id);
CREATE INDEX IF NOT EXISTS idx_reconciliacao_conta ON contas_a_receber_reconciliacao(conta_a_receber_id);
CREATE INDEX IF NOT EXISTS idx_reconciliacao_tipo_baixa ON contas_a_receber_reconciliacao(tipo_baixa);
