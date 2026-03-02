-- Migration: Criar tabela carvia_despesas
-- Executar no Render Shell

CREATE TABLE IF NOT EXISTS carvia_despesas (
    id SERIAL PRIMARY KEY,
    tipo_despesa VARCHAR(50) NOT NULL,
    descricao VARCHAR(500),
    valor NUMERIC(15, 2) NOT NULL,
    data_despesa DATE NOT NULL,
    data_vencimento DATE,
    status VARCHAR(20) DEFAULT 'PENDENTE',
    observacoes TEXT,
    criado_por VARCHAR(150),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_carvia_despesas_tipo_despesa
ON carvia_despesas (tipo_despesa);

CREATE INDEX IF NOT EXISTS ix_carvia_despesas_status
ON carvia_despesas (status);
