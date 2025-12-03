-- ============================================
-- MIGRAÇÃO: Criar tabela agent_sessions
-- Para uso no Shell do Render ou psql
-- FEAT-011: Lista de Sessões
-- ============================================

-- Verifica se tabela existe e cria com estrutura expandida
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'agent_sessions'
    ) THEN
        -- Cria tabela com campos para UI (FEAT-011)
        CREATE TABLE agent_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(100) UNIQUE NOT NULL,  -- ID do SDK
            user_id INTEGER REFERENCES usuarios(id),  -- FK para usuarios

            -- Campos para UI (FEAT-011)
            title VARCHAR(200),                        -- Título auto-gerado
            message_count INTEGER DEFAULT 0,           -- Contador de mensagens
            total_cost_usd DECIMAL(10, 6) DEFAULT 0,   -- Custo acumulado
            last_message TEXT,                         -- Preview da última msg
            model VARCHAR(100),                        -- Modelo usado

            -- Dados extras em JSONB
            data JSONB DEFAULT '{}',

            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Cria índices
        CREATE INDEX idx_agent_sessions_user_id ON agent_sessions(user_id);
        CREATE INDEX idx_agent_sessions_updated ON agent_sessions(updated_at DESC);
        CREATE INDEX idx_agent_sessions_session_id ON agent_sessions(session_id);

        RAISE NOTICE '✅ Tabela agent_sessions criada com sucesso!';
    ELSE
        RAISE NOTICE '⚠️ Tabela agent_sessions já existe.';
    END IF;
END $$;

-- Verifica estrutura criada
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agent_sessions'
ORDER BY ordinal_position;

-- Verifica índices
SELECT indexname FROM pg_indexes WHERE tablename = 'agent_sessions';
