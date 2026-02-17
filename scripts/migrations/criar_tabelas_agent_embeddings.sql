-- Migration: Criar tabelas session_turn_embeddings e agent_memory_embeddings
-- Fase 4 do Agent RAG
--
-- Executar no Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/criar_tabelas_agent_embeddings.sql
--
-- NOTA: Se pgvector disponivel, substituir TEXT por vector(1024) nas colunas embedding

-- ============================================================
-- session_turn_embeddings
-- ============================================================
CREATE TABLE IF NOT EXISTS session_turn_embeddings (
    id SERIAL PRIMARY KEY,

    -- Identificacao
    session_id VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL,
    turn_index INTEGER NOT NULL,

    -- Conteudo
    user_content TEXT NOT NULL,
    assistant_summary TEXT,
    texto_embedado TEXT NOT NULL,

    -- Embedding (TEXT fallback; usar vector(1024) se pgvector disponivel)
    embedding TEXT,
    model_used VARCHAR(50),
    content_hash VARCHAR(32),

    -- Metadata de sessao (denormalizado)
    session_title VARCHAR(200),
    session_created_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraint unica
    CONSTRAINT uq_session_turn UNIQUE (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS idx_ste_user_id ON session_turn_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_ste_session_id ON session_turn_embeddings(session_id);

-- ============================================================
-- agent_memory_embeddings
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_memory_embeddings (
    id SERIAL PRIMARY KEY,

    -- Identificacao
    memory_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    path VARCHAR(500) NOT NULL,

    -- Embedding
    texto_embedado TEXT NOT NULL,
    embedding TEXT,
    model_used VARCHAR(50),
    content_hash VARCHAR(32),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraint unica
    CONSTRAINT uq_memory_embedding UNIQUE (memory_id)
);

CREATE INDEX IF NOT EXISTS idx_ame_user_id ON agent_memory_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_ame_memory_id ON agent_memory_embeddings(memory_id);

-- ============================================================
-- Cascade delete: ao deletar agent_memories, limpa embedding
-- ============================================================
CREATE OR REPLACE FUNCTION fn_delete_memory_embedding()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM agent_memory_embeddings WHERE memory_id = OLD.id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_delete_memory_embedding ON agent_memories;

CREATE TRIGGER trg_delete_memory_embedding
BEFORE DELETE ON agent_memories
FOR EACH ROW
EXECUTE FUNCTION fn_delete_memory_embedding();

-- NOTA: IVFFlat indices devem ser criados APOS popular as tabelas (batch indexers)
-- Tabelas vazias falham ao criar indice IVFFlat
