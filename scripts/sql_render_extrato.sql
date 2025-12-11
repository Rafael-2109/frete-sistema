-- ============================================================================
-- SCRIPT SQL PARA CRIAR TABELAS DE EXTRATO BANCÁRIO NO RENDER
-- ============================================================================
-- Executar no Shell do PostgreSQL no Render
-- Data: 2025-12-11
-- ============================================================================

-- TABELA 1: Lotes de importação de extrato
CREATE TABLE IF NOT EXISTS extrato_lote (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    journal_code VARCHAR(20),
    journal_id INTEGER,
    data_inicio DATE,
    data_fim DATE,
    total_linhas INTEGER DEFAULT 0,
    linhas_com_match INTEGER DEFAULT 0,
    linhas_sem_match INTEGER DEFAULT 0,
    linhas_conciliadas INTEGER DEFAULT 0,
    linhas_erro INTEGER DEFAULT 0,
    valor_total FLOAT DEFAULT 0,
    status VARCHAR(30) DEFAULT 'IMPORTADO' NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    processado_em TIMESTAMP,
    processado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_extrato_lote_status ON extrato_lote(status);

-- TABELA 2: Itens de extrato
CREATE TABLE IF NOT EXISTS extrato_item (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES extrato_lote(id) ON DELETE CASCADE,

    -- Dados do Odoo
    statement_line_id INTEGER NOT NULL,
    move_id INTEGER,
    move_name VARCHAR(100),
    credit_line_id INTEGER,
    data_transacao DATE NOT NULL,
    valor FLOAT NOT NULL,
    payment_ref TEXT,

    -- Dados extraídos
    tipo_transacao VARCHAR(50),
    nome_pagador VARCHAR(255),
    cnpj_pagador VARCHAR(20),

    -- Journal
    journal_id INTEGER,
    journal_code VARCHAR(20),
    journal_name VARCHAR(100),

    -- Matching
    status_match VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
    titulo_id INTEGER,
    titulo_nf VARCHAR(50),
    titulo_parcela INTEGER,
    titulo_valor FLOAT,
    titulo_vencimento DATE,
    titulo_cliente VARCHAR(255),
    matches_candidatos TEXT,
    match_score INTEGER,
    match_criterio VARCHAR(100),

    -- Controle
    aprovado BOOLEAN DEFAULT FALSE NOT NULL,
    aprovado_em TIMESTAMP,
    aprovado_por VARCHAR(100),
    status VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
    mensagem TEXT,

    -- Resultado
    partial_reconcile_id INTEGER,
    full_reconcile_id INTEGER,
    titulo_saldo_antes FLOAT,
    titulo_saldo_depois FLOAT,
    snapshot_antes TEXT,
    snapshot_depois TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_extrato_item_lote ON extrato_item(lote_id);
CREATE INDEX IF NOT EXISTS idx_extrato_item_status ON extrato_item(status);
CREATE INDEX IF NOT EXISTS idx_extrato_item_cnpj ON extrato_item(cnpj_pagador);
CREATE INDEX IF NOT EXISTS idx_extrato_item_statement_line ON extrato_item(statement_line_id);

-- VERIFICAR CRIAÇÃO
SELECT 'extrato_lote' as tabela, count(*) as registros FROM extrato_lote
UNION ALL
SELECT 'extrato_item' as tabela, count(*) as registros FROM extrato_item;
