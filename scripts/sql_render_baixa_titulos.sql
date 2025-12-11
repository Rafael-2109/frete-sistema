-- ============================================================================
-- SCRIPT SQL PARA CRIAR TABELAS DE BAIXA DE TITULOS NO RENDER
-- ============================================================================
-- Executar no Shell do PostgreSQL no Render
-- Data: 2025-12-10
-- ============================================================================

-- TABELA 1: Lotes de importacao
CREATE TABLE IF NOT EXISTS baixa_titulo_lote (
    id SERIAL PRIMARY KEY,
    nome_arquivo VARCHAR(255) NOT NULL,
    hash_arquivo VARCHAR(64),
    total_linhas INTEGER DEFAULT 0,
    linhas_validas INTEGER DEFAULT 0,
    linhas_invalidas INTEGER DEFAULT 0,
    linhas_processadas INTEGER DEFAULT 0,
    linhas_sucesso INTEGER DEFAULT 0,
    linhas_erro INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'IMPORTADO' NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    processado_em TIMESTAMP,
    processado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_baixa_lote_status ON baixa_titulo_lote(status);

-- TABELA 2: Itens de baixa
CREATE TABLE IF NOT EXISTS baixa_titulo_item (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES baixa_titulo_lote(id) ON DELETE CASCADE,
    linha_excel INTEGER NOT NULL,

    -- Dados do Excel
    nf_excel VARCHAR(50) NOT NULL,
    parcela_excel INTEGER NOT NULL,
    valor_excel FLOAT NOT NULL,
    journal_excel VARCHAR(100) NOT NULL,
    data_excel DATE NOT NULL,

    -- Dados resolvidos do Odoo
    titulo_odoo_id INTEGER,
    move_odoo_id INTEGER,
    move_odoo_name VARCHAR(100),
    partner_odoo_id INTEGER,
    journal_odoo_id INTEGER,
    journal_odoo_code VARCHAR(20),
    valor_titulo_odoo FLOAT,
    saldo_antes FLOAT,

    -- Controle
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,
    mensagem TEXT,

    -- Resultado da operacao no Odoo
    payment_odoo_id INTEGER,
    payment_odoo_name VARCHAR(100),
    partial_reconcile_id INTEGER,
    saldo_depois FLOAT,

    -- Snapshots
    snapshot_antes TEXT,
    snapshot_depois TEXT,
    campos_alterados TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado_em TIMESTAMP,
    processado_em TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_baixa_item_lote ON baixa_titulo_item(lote_id);
CREATE INDEX IF NOT EXISTS idx_baixa_item_status ON baixa_titulo_item(status);
CREATE INDEX IF NOT EXISTS idx_baixa_item_nf ON baixa_titulo_item(nf_excel);

-- VERIFICAR CRIACAO
SELECT 'baixa_titulo_lote' as tabela, count(*) as registros FROM baixa_titulo_lote
UNION ALL
SELECT 'baixa_titulo_item' as tabela, count(*) as registros FROM baixa_titulo_item;
