-- ============================================
-- MIGRAÇÃO: Tabelas de Memória do Claude AI Lite
-- Executar no Shell do Render
-- ============================================

-- TABELA 1: Histórico de Conversas
CREATE TABLE IF NOT EXISTS claude_historico_conversa (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    tipo VARCHAR(20) NOT NULL,
    conteudo TEXT NOT NULL,
    metadados JSONB,
    criado_em TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Índices para histórico
CREATE INDEX IF NOT EXISTS idx_claude_hist_usuario ON claude_historico_conversa(usuario_id);
CREATE INDEX IF NOT EXISTS idx_claude_hist_tipo ON claude_historico_conversa(tipo);
CREATE INDEX IF NOT EXISTS idx_claude_hist_criado ON claude_historico_conversa(criado_em);
CREATE INDEX IF NOT EXISTS idx_claude_hist_usuario_data ON claude_historico_conversa(usuario_id, criado_em);

-- TABELA 2: Aprendizados Permanentes
CREATE TABLE IF NOT EXISTS claude_aprendizado (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    categoria VARCHAR(50) NOT NULL,
    chave VARCHAR(100) NOT NULL,
    valor TEXT NOT NULL,
    contexto JSONB,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    prioridade INTEGER DEFAULT 5 NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW() NOT NULL,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

-- Índices para aprendizado
CREATE INDEX IF NOT EXISTS idx_claude_aprend_usuario ON claude_aprendizado(usuario_id);
CREATE INDEX IF NOT EXISTS idx_claude_aprend_categoria ON claude_aprendizado(categoria);
CREATE INDEX IF NOT EXISTS idx_claude_aprend_chave ON claude_aprendizado(chave);
CREATE INDEX IF NOT EXISTS idx_claude_aprend_ativo ON claude_aprendizado(ativo);
CREATE INDEX IF NOT EXISTS idx_claude_aprend_usuario_cat ON claude_aprendizado(usuario_id, categoria);

-- Constraint de unicidade
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uk_claude_aprend_usuario_chave'
    ) THEN
        ALTER TABLE claude_aprendizado
        ADD CONSTRAINT uk_claude_aprend_usuario_chave
        UNIQUE (usuario_id, chave);
    END IF;
END $$;

-- VERIFICAÇÃO
SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'claude_%' ORDER BY table_name;
