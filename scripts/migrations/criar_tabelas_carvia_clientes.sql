-- Migration: Criar tabelas carvia_clientes + carvia_cliente_enderecos
-- Data: 2026-03-20
-- Uso: Executar no Render Shell (SQL idempotente)

CREATE TABLE IF NOT EXISTS carvia_clientes (
    id SERIAL PRIMARY KEY,
    nome_comercial VARCHAR(255) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes TEXT,
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS carvia_cliente_enderecos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL
        REFERENCES carvia_clientes(id) ON DELETE CASCADE,
    cnpj VARCHAR(20) NOT NULL,
    razao_social VARCHAR(255),

    -- Dados da Receita Federal (readonly)
    receita_uf VARCHAR(2),
    receita_cidade VARCHAR(100),
    receita_logradouro VARCHAR(255),
    receita_numero VARCHAR(20),
    receita_bairro VARCHAR(100),
    receita_cep VARCHAR(10),
    receita_complemento VARCHAR(255),

    -- Endereco fisico (editavel, pre-preenchido da Receita)
    fisico_uf VARCHAR(2),
    fisico_cidade VARCHAR(100),
    fisico_logradouro VARCHAR(255),
    fisico_numero VARCHAR(20),
    fisico_bairro VARCHAR(100),
    fisico_cep VARCHAR(10),
    fisico_complemento VARCHAR(255),

    -- Tipo e flags
    tipo VARCHAR(20) NOT NULL,
    principal BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL,

    CONSTRAINT uq_carvia_cliente_endereco UNIQUE (cliente_id, cnpj, tipo),
    CONSTRAINT ck_carvia_endereco_tipo CHECK (tipo IN ('ORIGEM', 'DESTINO'))
);

CREATE INDEX IF NOT EXISTS ix_carvia_cliente_end_cliente
    ON carvia_cliente_enderecos(cliente_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cliente_end_cnpj
    ON carvia_cliente_enderecos(cnpj);
CREATE INDEX IF NOT EXISTS ix_carvia_cliente_end_tipo
    ON carvia_cliente_enderecos(tipo);
