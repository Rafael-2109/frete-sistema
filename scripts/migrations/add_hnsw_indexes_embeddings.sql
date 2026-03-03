-- Migration: Criar indices HNSW para busca vetorial em embeddings
-- Suporta T2-3: Performance de busca semantica via pgvector
--
-- PREREQUISITO: pgvector instalado e tabelas populadas (batch indexers)
-- NOTA: CONCURRENTLY nao bloqueia reads/writes durante criacao
--
-- Executar no Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/add_hnsw_indexes_embeddings.sql

-- HNSW index para memorias do agente
-- m=16: numero de conexoes por nodo (default recomendado)
-- ef_construction=64: qualidade de construcao (tradeoff: mais alto = melhor recall, mais lento build)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memory_emb_hnsw
    ON agent_memory_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- HNSW index para turns de sessao
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_emb_hnsw
    ON session_turn_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Configurar ef_search para queries (balance recall vs speed)
-- Valor mais alto = melhor recall, mais lento
-- Default pgvector: 40. Recomendado: 100 para buscas de precisao
SET hnsw.ef_search = 100;
