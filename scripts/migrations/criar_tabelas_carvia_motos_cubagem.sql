-- Migration: Criar tabelas carvia_modelos_moto e carvia_empresas_cubagem
-- Idempotente — seguro para executar multiplas vezes

CREATE TABLE IF NOT EXISTS carvia_modelos_moto (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    regex_pattern VARCHAR(200),
    comprimento NUMERIC(10,4) NOT NULL,
    largura NUMERIC(10,4) NOT NULL,
    altura NUMERIC(10,4) NOT NULL,
    peso_medio NUMERIC(10,3),
    cubagem_minima NUMERIC(10,2) NOT NULL DEFAULT 300,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_modelos_moto_nome
    ON carvia_modelos_moto (nome);

CREATE TABLE IF NOT EXISTS carvia_empresas_cubagem (
    id SERIAL PRIMARY KEY,
    cnpj_empresa VARCHAR(20) NOT NULL,
    nome_empresa VARCHAR(255) NOT NULL,
    considerar_cubagem BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_empresas_cubagem_cnpj
    ON carvia_empresas_cubagem (cnpj_empresa);
