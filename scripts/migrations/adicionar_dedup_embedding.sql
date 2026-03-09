-- Migration: Adicionar coluna dedup_embedding em agent_memory_embeddings
-- Contexto: dedup de memórias comparava representações incompatíveis
-- (texto limpo vs embedding contextualizado), gerando falsos negativos.
--
-- Executar no Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/adicionar_dedup_embedding.sql

-- 1. Adicionar coluna
ALTER TABLE agent_memory_embeddings
ADD COLUMN IF NOT EXISTS dedup_embedding vector(1024);

-- 2. Criar índice HNSW para busca por similaridade
CREATE INDEX IF NOT EXISTS idx_hnsw_dedup_embedding
ON agent_memory_embeddings
USING hnsw (dedup_embedding vector_cosine_ops);
