-- Migration: Criar tabelas carvia_extrato_linhas e carvia_conciliacoes
-- Conciliacao bancaria CarVia
-- Uso: Render Shell → psql

-- carvia_extrato_linhas
CREATE TABLE IF NOT EXISTS carvia_extrato_linhas (
    id SERIAL PRIMARY KEY,
    fitid VARCHAR(100) NOT NULL,
    data DATE NOT NULL,
    valor NUMERIC(15, 2) NOT NULL,
    tipo VARCHAR(10) NOT NULL,
    descricao VARCHAR(500),
    memo VARCHAR(500),
    checknum VARCHAR(50),
    refnum VARCHAR(50),
    trntype VARCHAR(20),
    status_conciliacao VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    arquivo_ofx VARCHAR(255) NOT NULL,
    conta_bancaria VARCHAR(50),
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_carvia_extrato_fitid UNIQUE (fitid)
);

CREATE INDEX IF NOT EXISTS ix_carvia_extrato_data ON carvia_extrato_linhas (data);
CREATE INDEX IF NOT EXISTS ix_carvia_extrato_status ON carvia_extrato_linhas (status_conciliacao);
CREATE INDEX IF NOT EXISTS ix_carvia_extrato_arquivo ON carvia_extrato_linhas (arquivo_ofx);

-- carvia_conciliacoes
CREATE TABLE IF NOT EXISTS carvia_conciliacoes (
    id SERIAL PRIMARY KEY,
    extrato_linha_id INTEGER NOT NULL
        REFERENCES carvia_extrato_linhas(id) ON DELETE CASCADE,
    tipo_documento VARCHAR(30) NOT NULL,
    documento_id INTEGER NOT NULL,
    valor_alocado NUMERIC(15, 2) NOT NULL,
    conciliado_por VARCHAR(100) NOT NULL,
    conciliado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_carvia_conc_linha_doc
        UNIQUE (extrato_linha_id, tipo_documento, documento_id),
    CONSTRAINT ck_carvia_conc_valor CHECK (valor_alocado > 0)
);

CREATE INDEX IF NOT EXISTS ix_carvia_conc_linha ON carvia_conciliacoes (extrato_linha_id);
CREATE INDEX IF NOT EXISTS ix_carvia_conc_doc ON carvia_conciliacoes (tipo_documento, documento_id);
