-- Migração: Criar tabela agent_events para instrumentação de hooks
-- Executar no Shell do Render ou psql

-- Cria tabela (se não existir)
CREATE TABLE IF NOT EXISTS agent_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id),
    session_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices principais
CREATE INDEX IF NOT EXISTS ix_agent_events_user_id ON agent_events(user_id);
CREATE INDEX IF NOT EXISTS ix_agent_events_session_id ON agent_events(session_id);
CREATE INDEX IF NOT EXISTS ix_agent_events_event_type ON agent_events(event_type);

-- Índices compostos para queries comuns
CREATE INDEX IF NOT EXISTS ix_agent_events_user_session ON agent_events(user_id, session_id);
CREATE INDEX IF NOT EXISTS ix_agent_events_type_created ON agent_events(event_type, created_at);

-- Índice GIN para busca em JSONB
CREATE INDEX IF NOT EXISTS ix_agent_events_data_gin ON agent_events USING GIN (data);

-- Comentário na tabela
COMMENT ON TABLE agent_events IS 'Eventos do Agente para instrumentação (append-only)';
COMMENT ON COLUMN agent_events.event_type IS 'Tipo: session_start, pre_query, tool_call, tool_result, post_response, feedback_received, etc';
COMMENT ON COLUMN agent_events.data IS 'Dados do evento em JSONB';
