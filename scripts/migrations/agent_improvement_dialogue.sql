-- Migration: agent_improvement_dialogue
-- Tabela para dialogo versionado de melhoria continua entre Agent SDK e Claude Code.
-- Agent SDK escreve sugestoes (v1), Claude Code avalia/implementa (v2), Agent SDK verifica (v3).
--
-- Executar via Render Shell:
--   psql $DATABASE_URL -f agent_improvement_dialogue.sql

CREATE TABLE IF NOT EXISTS agent_improvement_dialogue (
    id SERIAL PRIMARY KEY,

    -- Identidade do dialogo
    suggestion_key VARCHAR(100) NOT NULL,   -- ex: "IMP-2026-03-31-001"
    version INTEGER NOT NULL DEFAULT 1,     -- turno do dialogo (max 3)

    -- Autoria e status
    author VARCHAR(20) NOT NULL,            -- 'agent_sdk' | 'claude_code'
    status VARCHAR(20) NOT NULL DEFAULT 'proposed',
    -- Lifecycle:
    --   proposed -> responded -> verified -> closed
    --   proposed -> rejected (por Claude Code)
    --   responded -> needs_revision (por Agent SDK, gera v3)

    -- Conteudo da sugestao/resposta
    category VARCHAR(30) NOT NULL,
    -- Categorias:
    --   skill_suggestion, instruction_request, prompt_feedback,
    --   gotcha_report, memory_feedback
    severity VARCHAR(10) NOT NULL DEFAULT 'info',   -- critical | warning | info
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    evidence_json JSONB DEFAULT '{}'::jsonb,

    -- Campos de resposta (preenchidos por Claude Code)
    affected_files TEXT[],
    implementation_notes TEXT,
    auto_implemented BOOLEAN DEFAULT FALSE,

    -- Rastreabilidade
    source_session_ids TEXT[],

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Uma suggestion_key so pode ter uma versao de cada numero
    UNIQUE(suggestion_key, version)
);

-- Indices para queries frequentes
CREATE INDEX IF NOT EXISTS idx_aid_status
    ON agent_improvement_dialogue(status);

CREATE INDEX IF NOT EXISTS idx_aid_key
    ON agent_improvement_dialogue(suggestion_key);

CREATE INDEX IF NOT EXISTS idx_aid_category_status
    ON agent_improvement_dialogue(category, status);

CREATE INDEX IF NOT EXISTS idx_aid_author_status
    ON agent_improvement_dialogue(author, status);

-- Indice parcial para sugestoes pendentes (query mais frequente do D8)
CREATE INDEX IF NOT EXISTS idx_aid_pending
    ON agent_improvement_dialogue(created_at ASC)
    WHERE status = 'proposed' AND author = 'agent_sdk';

-- Verificacao pos-migration
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'agent_improvement_dialogue'
    ) THEN
        RAISE NOTICE 'OK: tabela agent_improvement_dialogue criada com sucesso';
    ELSE
        RAISE EXCEPTION 'FALHA: tabela agent_improvement_dialogue NAO foi criada';
    END IF;
END $$;
