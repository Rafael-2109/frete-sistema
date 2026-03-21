-- Migration: Criar tabela carvia_config
-- Data: 2026-03-20
-- Descricao: Parametros globais do modulo CarVia (chave-valor)
-- Uso: Executar no Render Shell (SQL idempotente)

CREATE TABLE IF NOT EXISTS carvia_config (
    id SERIAL PRIMARY KEY,
    chave VARCHAR(50) NOT NULL UNIQUE,
    valor TEXT NOT NULL,
    descricao VARCHAR(255),
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100) NOT NULL
);

-- Seed: limite_desconto_percentual
INSERT INTO carvia_config (chave, valor, descricao, atualizado_por)
VALUES (
    'limite_desconto_percentual',
    '5.0',
    'Limite percentual de desconto que Jessica pode aprovar sem admin',
    'migration'
)
ON CONFLICT (chave) DO NOTHING;
