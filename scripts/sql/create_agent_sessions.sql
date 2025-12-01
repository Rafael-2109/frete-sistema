-- ============================================
-- MIGRAÇÃO: Criar tabela agent_sessions
-- Para uso no Shell do Render ou psql
-- ============================================

-- Verifica se tabela existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'agent_sessions'
    ) THEN
        -- Cria tabela
        CREATE TABLE agent_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(50) UNIQUE NOT NULL,
            user_id INTEGER,
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Cria índices
        CREATE INDEX idx_agent_sessions_user_id ON agent_sessions(user_id);
        CREATE INDEX idx_agent_sessions_updated ON agent_sessions(updated_at);
        CREATE INDEX idx_agent_sessions_data_gin ON agent_sessions USING gin(data);

        RAISE NOTICE 'Tabela agent_sessions criada com sucesso!';
    ELSE
        RAISE NOTICE 'Tabela agent_sessions já existe.';
    END IF;
END $$;

-- Verifica estrutura
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agent_sessions'
ORDER BY ordinal_position;
