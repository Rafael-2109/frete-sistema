-- =====================================================================
-- Migration: Converter colunas embedding de TEXT para vector(1024)
-- Data: 2026-02-17
--
-- Problema: session_turn_embeddings e agent_memory_embeddings foram
-- criadas com embedding TEXT. Indices HNSW requerem tipo vector nativo.
--
-- Pre-requisito: extensao pgvector ja instalada (CREATE EXTENSION vector)
--
-- IMPORTANTE: Rows com embedding NULL ou vazio sao ignoradas pelo USING.
-- Rows com embedding invalido (nao-JSON array) causarao erro.
-- =====================================================================

-- 1. session_turn_embeddings: TEXT → vector(1024)
ALTER TABLE session_turn_embeddings
    ALTER COLUMN embedding TYPE vector(1024)
    USING embedding::vector(1024);

-- 2. agent_memory_embeddings: TEXT → vector(1024)
ALTER TABLE agent_memory_embeddings
    ALTER COLUMN embedding TYPE vector(1024)
    USING embedding::vector(1024);

-- 3. Re-criar indices HNSW que falharam
CREATE INDEX IF NOT EXISTS idx_hnsw_session_turn_embedding
    ON session_turn_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_hnsw_agent_memory_embedding
    ON agent_memory_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =====================================================================
-- VERIFICACAO
-- =====================================================================
-- SELECT column_name, udt_name
-- FROM information_schema.columns
-- WHERE table_name IN ('session_turn_embeddings', 'agent_memory_embeddings')
--   AND column_name = 'embedding';
-- Deve retornar: udt_name = 'vector' para ambas
