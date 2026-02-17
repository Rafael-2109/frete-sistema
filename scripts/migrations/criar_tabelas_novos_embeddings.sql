-- Migration: Criar tabelas de embeddings — novos dominios
-- Executar via Render Shell ou psql
-- Idempotente: IF NOT EXISTS em todos os DDL
-- Pre-requisito: extensao pgvector ja habilitada

-- ============================================================
-- 1. sql_template_embeddings
-- ============================================================
CREATE TABLE IF NOT EXISTS sql_template_embeddings (
    id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    sql_text TEXT NOT NULL,
    tables_used TEXT,
    execution_count INTEGER NOT NULL DEFAULT 1,
    last_used_at TIMESTAMP,
    texto_embedado TEXT NOT NULL,
    embedding vector(1024),
    model_used VARCHAR(50),
    content_hash VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sqlt_content_hash
    ON sql_template_embeddings(content_hash);

-- IVFFlat: criar apos popular tabela (requer > lists registros)
-- CREATE INDEX IF NOT EXISTS idx_sqlt_emb_cosine
--     ON sql_template_embeddings
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 10);

-- ============================================================
-- 2. payment_category_embeddings
-- ============================================================
CREATE TABLE IF NOT EXISTS payment_category_embeddings (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    examples TEXT,
    texto_embedado TEXT NOT NULL,
    embedding vector(1024),
    model_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- IVFFlat: ~10 categorias, lists=5
-- CREATE INDEX IF NOT EXISTS idx_paycat_emb_cosine
--     ON payment_category_embeddings
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 5);

-- ============================================================
-- 3. devolucao_reason_embeddings
-- ============================================================
CREATE TABLE IF NOT EXISTS devolucao_reason_embeddings (
    id SERIAL PRIMARY KEY,
    nf_devolucao_linha_id INTEGER,
    descricao_text TEXT NOT NULL,
    motivo_classificado VARCHAR(50),
    texto_embedado TEXT NOT NULL,
    embedding vector(1024),
    model_used VARCHAR(50),
    content_hash VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dre_motivo
    ON devolucao_reason_embeddings(motivo_classificado);

CREATE INDEX IF NOT EXISTS idx_dre_content_hash
    ON devolucao_reason_embeddings(content_hash);

-- IVFFlat: criar apos popular
-- CREATE INDEX IF NOT EXISTS idx_dre_emb_cosine
--     ON devolucao_reason_embeddings
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 10);

-- ============================================================
-- 4. carrier_embeddings
-- ============================================================
CREATE TABLE IF NOT EXISTS carrier_embeddings (
    id SERIAL PRIMARY KEY,
    carrier_name TEXT NOT NULL,
    cnpj VARCHAR(20),
    aliases TEXT,
    texto_embedado TEXT NOT NULL,
    embedding vector(1024),
    model_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_carrier_name UNIQUE (carrier_name)
);

CREATE INDEX IF NOT EXISTS idx_carrier_name
    ON carrier_embeddings(carrier_name);

-- IVFFlat: criar apos popular
-- CREATE INDEX IF NOT EXISTS idx_carrier_emb_cosine
--     ON carrier_embeddings
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 10);
