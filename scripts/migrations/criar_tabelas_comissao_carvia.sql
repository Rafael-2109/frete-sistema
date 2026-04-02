-- Migration: Criar tabelas de comissao CarVia
-- Executar no Render Shell: psql $DATABASE_URL < scripts/migrations/criar_tabelas_comissao_carvia.sql

-- Tabela principal: fechamentos de comissao
CREATE TABLE IF NOT EXISTS carvia_comissao_fechamentos (
    id SERIAL PRIMARY KEY,
    numero_fechamento VARCHAR(20) NOT NULL UNIQUE,
    vendedor_nome VARCHAR(100) NOT NULL,
    vendedor_email VARCHAR(150),
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    percentual NUMERIC(5, 4) NOT NULL,
    qtd_ctes INTEGER NOT NULL DEFAULT 0,
    total_bruto NUMERIC(15, 2) NOT NULL DEFAULT 0,
    total_comissao NUMERIC(15, 2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    pago_por VARCHAR(100),
    pago_em TIMESTAMP,
    data_pagamento DATE,
    observacoes TEXT,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    CONSTRAINT ck_comissao_periodo_valido CHECK (data_inicio <= data_fim),
    CONSTRAINT ck_comissao_percentual_range CHECK (percentual > 0 AND percentual <= 1),
    CONSTRAINT ck_comissao_status_valido CHECK (status IN ('PENDENTE', 'PAGO', 'CANCELADO'))
);

CREATE INDEX IF NOT EXISTS idx_comissao_fechamentos_status ON carvia_comissao_fechamentos (status);
CREATE INDEX IF NOT EXISTS idx_comissao_fechamentos_data_inicio ON carvia_comissao_fechamentos (data_inicio);
CREATE INDEX IF NOT EXISTS idx_comissao_fechamentos_vendedor ON carvia_comissao_fechamentos (vendedor_email);

-- Junction: CTes vinculados ao fechamento (com snapshots)
CREATE TABLE IF NOT EXISTS carvia_comissao_fechamento_ctes (
    id SERIAL PRIMARY KEY,
    fechamento_id INTEGER NOT NULL REFERENCES carvia_comissao_fechamentos(id) ON DELETE CASCADE,
    operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
    cte_numero VARCHAR(20) NOT NULL,
    cte_data_emissao DATE NOT NULL,
    valor_cte_snapshot NUMERIC(15, 2) NOT NULL,
    percentual_snapshot NUMERIC(5, 4) NOT NULL,
    valor_comissao NUMERIC(15, 2) NOT NULL,
    excluido BOOLEAN NOT NULL DEFAULT FALSE,
    excluido_em TIMESTAMP,
    excluido_por VARCHAR(100),
    incluido_por VARCHAR(100) NOT NULL,
    incluido_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_comissao_fechamento_operacao UNIQUE (fechamento_id, operacao_id)
);

CREATE INDEX IF NOT EXISTS idx_comissao_fctes_fechamento_id ON carvia_comissao_fechamento_ctes (fechamento_id);
CREATE INDEX IF NOT EXISTS idx_comissao_fctes_operacao_id ON carvia_comissao_fechamento_ctes (operacao_id);
CREATE INDEX IF NOT EXISTS idx_comissao_fctes_excluido ON carvia_comissao_fechamento_ctes (fechamento_id, excluido);
