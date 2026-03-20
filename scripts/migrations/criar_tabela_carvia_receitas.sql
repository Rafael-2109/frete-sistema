-- Migration: Criar tabela carvia_receitas
-- Receitas operacionais diversas do modulo CarVia
-- Uso: Render Shell (psql)

CREATE TABLE IF NOT EXISTS carvia_receitas (
    id SERIAL PRIMARY KEY,
    tipo_receita VARCHAR(50) NOT NULL,
    descricao VARCHAR(500),
    valor NUMERIC(15, 2) NOT NULL,
    data_receita DATE NOT NULL,
    data_vencimento DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    recebido_por VARCHAR(100),
    recebido_em TIMESTAMP,
    total_conciliado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    conciliado BOOLEAN NOT NULL DEFAULT FALSE,
    observacoes TEXT,
    criado_por VARCHAR(150),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_carvia_receitas_tipo_receita
    ON carvia_receitas (tipo_receita);

CREATE INDEX IF NOT EXISTS ix_carvia_receitas_status
    ON carvia_receitas (status);
