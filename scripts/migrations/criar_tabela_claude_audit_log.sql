-- Migração: Criar tabela claude_audit_log
-- Para rodar no Shell do Render (PostgreSQL)
--
-- Esta tabela armazena logs de auditoria das operações do Claude Code

-- Criar tabela
CREATE TABLE IF NOT EXISTS claude_audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    tool VARCHAR(50),
    file_path TEXT,
    user_name VARCHAR(100),
    session_id VARCHAR(100),
    operation_type VARCHAR(50),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_claude_audit_timestamp
ON claude_audit_log(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_claude_audit_operation_type
ON claude_audit_log(operation_type);

CREATE INDEX IF NOT EXISTS idx_claude_audit_file_path
ON claude_audit_log(file_path);

-- Comentários
COMMENT ON TABLE claude_audit_log IS
'Logs de auditoria das operações do Claude Code (hooks)';

COMMENT ON COLUMN claude_audit_log.operation_type IS
'Tipo: separacao, notificacao_info, notificacao_warning, notificacao_critical';

-- Verificar criação
SELECT 'Tabela criada com sucesso!' as status;
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'claude_audit_log' ORDER BY ordinal_position;
