-- Migration: Embeddings de regras normativas do Manual ECD Leiaute 9
-- Data: 2026-05-16
-- Reversao: DROP TABLE sped_ecd_rule_embeddings;

CREATE TABLE IF NOT EXISTS sped_ecd_rule_embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(120) NOT NULL UNIQUE,
    chunk_type VARCHAR(20) NOT NULL,
    bloco VARCHAR(2),
    registro VARCHAR(8),
    regra_name VARCHAR(120),
    severidade VARCHAR(20),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(1024) NOT NULL,
    model VARCHAR(40) NOT NULL DEFAULT 'voyage-4-lite',
    source_file VARCHAR(200),
    source_anchor VARCHAR(120),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_chunk_id ON sped_ecd_rule_embeddings (chunk_id);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_chunk_type ON sped_ecd_rule_embeddings (chunk_type);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_bloco ON sped_ecd_rule_embeddings (bloco);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_registro ON sped_ecd_rule_embeddings (registro);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_regra_name ON sped_ecd_rule_embeddings (regra_name);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_hash ON sped_ecd_rule_embeddings (content_hash);

CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_cosine
    ON sped_ecd_rule_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
