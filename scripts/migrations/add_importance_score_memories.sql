-- Migration: Adicionar importance_score e last_accessed_at a agent_memories
-- Suporta QW-1: Memory Importance Scoring + Decay
--
-- Executar no Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/add_importance_score_memories.sql

-- importance_score: float 0-1, heuristico baseado em conteudo
ALTER TABLE agent_memories
    ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.5;

-- last_accessed_at: timestamp da ultima injecao/leitura
ALTER TABLE agent_memories
    ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMP DEFAULT NOW();

-- Indice para queries de retrieval com decay (ordenar por last_accessed_at)
CREATE INDEX IF NOT EXISTS idx_agent_memories_last_accessed
    ON agent_memories (user_id, last_accessed_at DESC);

-- Indice para queries com importance_score
CREATE INDEX IF NOT EXISTS idx_agent_memories_importance
    ON agent_memories (user_id, importance_score DESC);

-- Backfill: setar last_accessed_at = updated_at para registros existentes
UPDATE agent_memories
SET last_accessed_at = COALESCE(updated_at, created_at, NOW())
WHERE last_accessed_at IS NULL OR last_accessed_at = NOW();
