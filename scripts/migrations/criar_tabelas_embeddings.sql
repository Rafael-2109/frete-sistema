-- ============================================================
-- Migration: Criar extensao pgvector e tabelas de embeddings
-- Executar via Render Shell (SQL idempotente)
-- ============================================================

-- [1/3] Habilitar extensao pgvector
-- Se nao disponivel no Render, ignorar e usar TEXT fallback
CREATE EXTENSION IF NOT EXISTS vector;

-- [2/3] Tabela ssw_document_embeddings
-- Armazena chunks da documentacao SSW com embeddings para busca semantica
CREATE TABLE IF NOT EXISTS ssw_document_embeddings (
    id SERIAL PRIMARY KEY,

    -- Identificacao do chunk
    doc_path TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    heading TEXT,
    doc_title TEXT,

    -- Embedding (vector(1024) com pgvector, TEXT sem)
    embedding vector(1024),

    -- Metadados
    char_count INTEGER,
    token_count INTEGER,
    model_used VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraint unica
    CONSTRAINT uq_ssw_doc_chunk UNIQUE (doc_path, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_ssw_emb_doc_path
    ON ssw_document_embeddings(doc_path);

-- Indice IVFFlat para busca por cosine similarity
-- NOTA: Pode falhar se tabela vazia (IVFFlat precisa de dados para treinar)
-- Recriar apos popular a tabela se necessario:
-- DROP INDEX IF EXISTS idx_ssw_emb_cosine;
-- CREATE INDEX idx_ssw_emb_cosine ON ssw_document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- [3/3] Tabela product_embeddings
-- Armazena embeddings de produtos para matching semantico
CREATE TABLE IF NOT EXISTS product_embeddings (
    id SERIAL PRIMARY KEY,

    -- Identificacao do produto
    cod_produto VARCHAR(50) NOT NULL UNIQUE,
    nome_produto TEXT NOT NULL,
    tipo_materia_prima VARCHAR(100),
    texto_embedado TEXT NOT NULL,

    -- Embedding
    embedding vector(1024),

    -- Metadados
    model_used VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prod_emb_cod
    ON product_embeddings(cod_produto);

-- Verificacao
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('ssw_document_embeddings', 'product_embeddings')
ORDER BY table_name;
