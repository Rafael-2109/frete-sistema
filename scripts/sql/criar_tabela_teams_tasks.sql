-- Migration: Cria tabela teams_tasks para processamento assíncrono do bot do Teams
-- Executar no Render Shell: psql $DATABASE_URL < scripts/sql/criar_tabela_teams_tasks.sql

CREATE TABLE IF NOT EXISTS teams_tasks (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    user_name VARCHAR(200) NOT NULL,
    user_id INTEGER REFERENCES usuarios(id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    mensagem TEXT NOT NULL,
    resposta TEXT,
    pending_questions JSON,
    pending_question_session_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_teams_tasks_conversation_id ON teams_tasks (conversation_id);
CREATE INDEX IF NOT EXISTS ix_teams_tasks_status ON teams_tasks (status);
CREATE INDEX IF NOT EXISTS ix_teams_tasks_created_at ON teams_tasks (created_at);
CREATE INDEX IF NOT EXISTS ix_teams_tasks_conv_status ON teams_tasks (conversation_id, status);
