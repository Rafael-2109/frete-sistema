-- Migration S1: embeddings do CATALOGO DE TABELAS (busca semantica de tabela por intencao)
-- Data: 2026-06-07
-- Subsistema S1 (progressive disclosure) do pacote text-to-sql.
-- Alimenta a tool buscar_tabelas (camada semantica), fundida com a busca textual.
-- Reversao: DROP TABLE table_catalog_embeddings;
--
-- Uso PROD (Render Shell):
--     psql $DATABASE_URL -f scripts/migrations/2026_06_07_table_catalog_embeddings.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS table_catalog_embeddings (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(120) NOT NULL UNIQUE,
    dominio VARCHAR(80),
    descricao TEXT,
    key_fields TEXT,
    texto_embedado TEXT NOT NULL,
    embedding vector(1024),
    model_used VARCHAR(50),
    content_hash VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- table_name UNIQUE ja cria indice unico implicito (chave de upsert).
CREATE INDEX IF NOT EXISTS ix_table_catalog_embed_hash ON table_catalog_embeddings (content_hash);

-- Indice HNSW para busca por similaridade de cosseno (operador <=>).
CREATE INDEX IF NOT EXISTS ix_table_catalog_embed_cosine
    ON table_catalog_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
