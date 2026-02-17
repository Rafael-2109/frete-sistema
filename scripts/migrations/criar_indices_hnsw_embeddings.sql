-- =====================================================================
-- Migration: Criar indices HNSW para 9 tabelas de embeddings
-- Data: 2026-02-17
-- Autor: Claude Code
--
-- HNSW vs IVFFlat:
--   - HNSW funciona em tabelas VAZIAS (IVFFlat requer dados para treinar)
--   - HNSW tem melhor recall (>99% vs ~95% do IVFFlat)
--   - HNSW consome mais memoria mas e mais rapido em buscas
--
-- Parametros: m=16, ef_construction=64 (defaults recomendados pgvector)
-- Operador: vector_cosine_ops (cosine distance, usado por <=>)
--
-- Inclui: indice unico parcial em content_hash para devolucao_reason_embeddings
-- =====================================================================

-- Extensao pgvector (idempotente)
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================================
-- HNSW INDICES (9 tabelas)
-- =====================================================================

-- 1. SSW Document Embeddings (~3K chunks)
CREATE INDEX IF NOT EXISTS idx_hnsw_ssw_embedding
    ON ssw_document_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 2. Product Embeddings (~5K produtos)
CREATE INDEX IF NOT EXISTS idx_hnsw_product_embedding
    ON product_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 3. Financial Entity Embeddings (~20K entities)
CREATE INDEX IF NOT EXISTS idx_hnsw_financial_entity_embedding
    ON financial_entity_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 4. Session Turn Embeddings (cresce indefinidamente)
CREATE INDEX IF NOT EXISTS idx_hnsw_session_turn_embedding
    ON session_turn_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 5. Agent Memory Embeddings (~500 memorias)
CREATE INDEX IF NOT EXISTS idx_hnsw_agent_memory_embedding
    ON agent_memory_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 6. SQL Template Embeddings (~100 templates)
CREATE INDEX IF NOT EXISTS idx_hnsw_sql_template_embedding
    ON sql_template_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 7. Payment Category Embeddings (~12 categorias)
CREATE INDEX IF NOT EXISTS idx_hnsw_payment_category_embedding
    ON payment_category_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 8. Devolucao Reason Embeddings (~1K motivos)
CREATE INDEX IF NOT EXISTS idx_hnsw_devolucao_reason_embedding
    ON devolucao_reason_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 9. Carrier Embeddings (~500 transportadoras)
CREATE INDEX IF NOT EXISTS idx_hnsw_carrier_embedding
    ON carrier_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =====================================================================
-- INDICE UNICO PARCIAL para devolucao_reason_embeddings.content_hash
-- Necessario para ON CONFLICT (content_hash) no upsert do indexer
-- =====================================================================

-- Remover indice antigo nao-unico (se existir)
DROP INDEX IF EXISTS idx_dre_content_hash;

-- Criar indice unico parcial (ignora NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dre_content_hash_unique
    ON devolucao_reason_embeddings (content_hash)
    WHERE content_hash IS NOT NULL;

-- =====================================================================
-- VERIFICACAO
-- =====================================================================

-- Listar todos os indices criados:
-- SELECT indexname, tablename FROM pg_indexes WHERE indexname LIKE 'idx_hnsw_%' ORDER BY tablename;
