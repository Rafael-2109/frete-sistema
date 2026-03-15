-- Migration: Criar tabelas para Cotacao CarVia v2
-- 4 tabelas: grupos_cliente -> membros -> tabelas_frete -> cidades_atendidas
-- Executar no Render Shell

-- 1. Grupos de Cliente
CREATE TABLE IF NOT EXISTS carvia_grupos_cliente (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL UNIQUE,
    descricao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL
);

-- 2. Membros (CNPJs) do grupo
CREATE TABLE IF NOT EXISTS carvia_grupo_cliente_membros (
    id SERIAL PRIMARY KEY,
    grupo_id INTEGER NOT NULL REFERENCES carvia_grupos_cliente(id) ON DELETE CASCADE,
    cnpj VARCHAR(20) NOT NULL,
    nome_empresa VARCHAR(255),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL,
    CONSTRAINT uq_carvia_grupo_membro UNIQUE (grupo_id, cnpj)
);
CREATE INDEX IF NOT EXISTS ix_carvia_grupo_membro_grupo_id ON carvia_grupo_cliente_membros (grupo_id);
CREATE INDEX IF NOT EXISTS ix_carvia_grupo_membro_cnpj ON carvia_grupo_cliente_membros (cnpj);

-- 3. Tabelas de frete CarVia (preco de venda)
CREATE TABLE IF NOT EXISTS carvia_tabelas_frete (
    id SERIAL PRIMARY KEY,
    uf_origem VARCHAR(2) NOT NULL,
    uf_destino VARCHAR(2) NOT NULL,
    nome_tabela VARCHAR(50) NOT NULL,
    tipo_carga VARCHAR(20) NOT NULL,
    modalidade VARCHAR(50) NOT NULL,
    grupo_cliente_id INTEGER REFERENCES carvia_grupos_cliente(id),
    valor_kg FLOAT,
    frete_minimo_peso FLOAT,
    percentual_valor FLOAT,
    frete_minimo_valor FLOAT,
    percentual_gris FLOAT,
    percentual_adv FLOAT,
    percentual_rca FLOAT,
    pedagio_por_100kg FLOAT,
    valor_despacho FLOAT,
    valor_cte FLOAT,
    valor_tas FLOAT,
    icms_incluso BOOLEAN NOT NULL DEFAULT FALSE,
    gris_minimo FLOAT DEFAULT 0,
    adv_minimo FLOAT DEFAULT 0,
    icms_proprio FLOAT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL,
    CONSTRAINT ck_carvia_tf_tipo_carga CHECK (tipo_carga IN ('DIRETA', 'FRACIONADA'))
);
CREATE INDEX IF NOT EXISTS ix_carvia_tf_uf ON carvia_tabelas_frete (uf_origem, uf_destino);
CREATE INDEX IF NOT EXISTS ix_carvia_tf_grupo_cliente_id ON carvia_tabelas_frete (grupo_cliente_id);
CREATE INDEX IF NOT EXISTS ix_carvia_tf_tipo_carga ON carvia_tabelas_frete (tipo_carga);

-- 4. Cidades atendidas CarVia
CREATE TABLE IF NOT EXISTS carvia_cidades_atendidas (
    id SERIAL PRIMARY KEY,
    codigo_ibge VARCHAR(10) NOT NULL,
    nome_cidade VARCHAR(100) NOT NULL,
    uf VARCHAR(2) NOT NULL,
    nome_tabela VARCHAR(50) NOT NULL,
    lead_time INTEGER,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100) NOT NULL,
    CONSTRAINT uq_carvia_cidade_tabela UNIQUE (codigo_ibge, nome_tabela)
);
CREATE INDEX IF NOT EXISTS ix_carvia_cidade_ibge ON carvia_cidades_atendidas (codigo_ibge);
CREATE INDEX IF NOT EXISTS ix_carvia_cidade_uf ON carvia_cidades_atendidas (uf);
