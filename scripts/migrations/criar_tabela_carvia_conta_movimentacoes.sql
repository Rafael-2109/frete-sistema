-- Migration: Criar tabela carvia_conta_movimentacoes
-- Registra movimentacoes financeiras da conta CarVia
-- Executar via Render Shell (idempotente)

CREATE TABLE IF NOT EXISTS carvia_conta_movimentacoes (
    id SERIAL PRIMARY KEY,
    tipo_doc VARCHAR(30) NOT NULL,
    doc_id INTEGER NOT NULL,
    tipo_movimento VARCHAR(10) NOT NULL,
    valor NUMERIC(15, 2) NOT NULL,
    descricao VARCHAR(500),
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_carvia_mov_tipo_doc UNIQUE (tipo_doc, doc_id),
    CONSTRAINT ck_carvia_mov_tipo CHECK (tipo_movimento IN ('CREDITO', 'DEBITO')),
    CONSTRAINT ck_carvia_mov_valor CHECK (valor > 0)
);

CREATE INDEX IF NOT EXISTS ix_carvia_mov_criado_em
ON carvia_conta_movimentacoes (criado_em);
