-- ============================================================
-- Migration: Criar tabela financial_entity_embeddings
-- Executar via Render Shell (SQL idempotente)
-- ============================================================

-- Tabela de embeddings para entidades financeiras (fornecedores/clientes)
-- Agrupa por CNPJ raiz (8 digitos) para matching semantico
CREATE TABLE IF NOT EXISTS financial_entity_embeddings (
    id SERIAL PRIMARY KEY,

    -- Identificacao
    entity_type VARCHAR(20) NOT NULL,        -- 'supplier' ou 'customer'
    cnpj_raiz VARCHAR(8) NOT NULL,           -- 8 digitos (grupo empresarial)
    cnpj_completo VARCHAR(20),               -- Um CNPJ representativo
    nome TEXT NOT NULL,                       -- Nome canonico (longest raz_social)
    nomes_alternativos TEXT,                  -- JSON: variacoes conhecidas
    texto_embedado TEXT NOT NULL,             -- Texto usado para embedding

    -- Embedding (vector(1024) com pgvector, TEXT sem)
    embedding vector(1024),
    model_used VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraint unica
    CONSTRAINT uq_fin_entity_type_cnpj UNIQUE (entity_type, cnpj_raiz)
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_fin_entity_type
    ON financial_entity_embeddings(entity_type);

CREATE INDEX IF NOT EXISTS idx_fin_entity_cnpj_raiz
    ON financial_entity_embeddings(cnpj_raiz);

-- Indice IVFFlat para busca por cosine similarity
-- NOTA: Pode falhar se tabela vazia (IVFFlat precisa de dados para treinar)
-- Recriar apos popular a tabela se necessario:
-- DROP INDEX IF EXISTS idx_fin_entity_emb_cosine;
-- CREATE INDEX idx_fin_entity_emb_cosine ON financial_entity_embeddings
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 30);

-- Verificacao
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'financial_entity_embeddings';
