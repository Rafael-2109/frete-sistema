-- Script SQL para criar tabela claude_perguntas_nao_respondidas
-- Para executar no Shell do Render
-- Criado em: 23/11/2025

-- Verifica se tabela existe e cria se não existir
CREATE TABLE IF NOT EXISTS claude_perguntas_nao_respondidas (
    id SERIAL PRIMARY KEY,

    -- Vínculo com usuário
    usuario_id INTEGER REFERENCES usuarios(id),

    -- Pergunta original
    consulta TEXT NOT NULL,

    -- Classificação detectada
    intencao_detectada VARCHAR(50),
    dominio_detectado VARCHAR(50),
    confianca FLOAT,

    -- Entidades extraídas (JSON)
    entidades JSONB,

    -- Motivo da falha
    -- Valores: 'sem_capacidade', 'sem_criterio', 'erro_execucao', 'sem_resultado', 'pergunta_composta'
    motivo_falha VARCHAR(100) NOT NULL,

    -- Análise da complexidade
    -- Valores: 'simples', 'composta', 'ambigua'
    tipo_pergunta VARCHAR(20) DEFAULT 'simples',
    dimensoes_detectadas JSONB,

    -- Sugestão oferecida ao usuário
    sugestao_gerada TEXT,

    -- Status de tratamento
    -- Valores: 'pendente', 'analisado', 'implementado', 'ignorado'
    status VARCHAR(20) DEFAULT 'pendente',

    -- Notas de análise (preenchido manualmente depois)
    notas_analise TEXT,
    capacidade_sugerida VARCHAR(100),

    -- Timestamps
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    analisado_em TIMESTAMP,
    analisado_por VARCHAR(100)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_claude_nao_resp_usuario
ON claude_perguntas_nao_respondidas(usuario_id);

CREATE INDEX IF NOT EXISTS idx_claude_nao_resp_motivo_data
ON claude_perguntas_nao_respondidas(motivo_falha, criado_em);

CREATE INDEX IF NOT EXISTS idx_claude_nao_resp_status
ON claude_perguntas_nao_respondidas(status, criado_em);

CREATE INDEX IF NOT EXISTS idx_claude_nao_resp_tipo
ON claude_perguntas_nao_respondidas(tipo_pergunta);

CREATE INDEX IF NOT EXISTS idx_claude_nao_resp_criado
ON claude_perguntas_nao_respondidas(criado_em);

-- Comentários
COMMENT ON TABLE claude_perguntas_nao_respondidas IS 'Log de perguntas que o Claude AI Lite não conseguiu responder';
COMMENT ON COLUMN claude_perguntas_nao_respondidas.motivo_falha IS 'sem_capacidade, sem_criterio, erro_execucao, sem_resultado, pergunta_composta';
COMMENT ON COLUMN claude_perguntas_nao_respondidas.tipo_pergunta IS 'simples, composta, ambigua';
COMMENT ON COLUMN claude_perguntas_nao_respondidas.status IS 'pendente, analisado, implementado, ignorado';
COMMENT ON COLUMN claude_perguntas_nao_respondidas.dimensoes_detectadas IS 'Array de dimensões: cliente, data, estoque, produto, etc';

-- Verificação
SELECT 'Tabela claude_perguntas_nao_respondidas criada com sucesso!' AS resultado;
