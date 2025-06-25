-- 🧠 BANCO DE CONHECIMENTO VITALÍCIO DO CLAUDE AI
-- Sistema de aprendizado permanente e evolutivo

-- 1. PADRÕES DE CONSULTA APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_knowledge_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL, -- 'cliente', 'periodo', 'dominio', 'intencao'
    pattern_text TEXT NOT NULL, -- Texto do padrão detectado
    interpretation JSONB NOT NULL, -- Como interpretar esse padrão
    confidence FLOAT DEFAULT 0.5, -- Confiança no padrão (0-1)
    usage_count INTEGER DEFAULT 1, -- Quantas vezes foi usado
    success_rate FLOAT DEFAULT 0.5, -- Taxa de sucesso
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    UNIQUE(pattern_type, pattern_text)
);

-- 2. MAPEAMENTOS SEMÂNTICOS APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_semantic_mappings (
    id SERIAL PRIMARY KEY,
    termo_usuario TEXT NOT NULL, -- Como o usuário se refere
    campo_sistema VARCHAR(100) NOT NULL, -- Campo real no sistema
    modelo VARCHAR(50) NOT NULL, -- Modelo/tabela
    contexto TEXT, -- Contexto onde foi usado
    frequencia INTEGER DEFAULT 1,
    ultima_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado BOOLEAN DEFAULT FALSE,
    validado_por VARCHAR(100),
    validado_em TIMESTAMP,
    UNIQUE(termo_usuario, campo_sistema, modelo)
);

-- 3. CORREÇÕES E FEEDBACK HISTÓRICO
CREATE TABLE IF NOT EXISTS ai_learning_history (
    id SERIAL PRIMARY KEY,
    consulta_original TEXT NOT NULL,
    interpretacao_inicial JSONB NOT NULL,
    resposta_inicial TEXT,
    feedback_usuario TEXT,
    interpretacao_corrigida JSONB,
    resposta_corrigida TEXT,
    tipo_correcao VARCHAR(50), -- 'cliente_errado', 'periodo_errado', 'dominio_errado'
    aprendizado_extraido JSONB, -- O que foi aprendido
    usuario_id INTEGER,
    sessao_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. GRUPOS EMPRESARIAIS APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_grupos_empresariais (
    id SERIAL PRIMARY KEY,
    nome_grupo VARCHAR(200) NOT NULL UNIQUE,
    tipo_negocio VARCHAR(100),
    cnpj_prefixos TEXT[], -- Array de prefixos CNPJ
    palavras_chave TEXT[], -- Palavras para detectar
    filtro_sql TEXT NOT NULL,
    regras_deteccao JSONB, -- Regras complexas
    estatisticas JSONB, -- Dados estatísticos do grupo
    ativo BOOLEAN DEFAULT TRUE,
    aprendido_automaticamente BOOLEAN DEFAULT FALSE,
    confirmado_por VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. CONTEXTOS DE NEGÓCIO APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_business_contexts (
    id SERIAL PRIMARY KEY,
    contexto_nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    regras JSONB NOT NULL, -- Regras de negócio específicas
    exemplos JSONB, -- Exemplos de uso
    restricoes JSONB, -- Restrições e validações
    prioridade INTEGER DEFAULT 50,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. RESPOSTAS MODELO (TEMPLATES APRENDIDOS)
CREATE TABLE IF NOT EXISTS ai_response_templates (
    id SERIAL PRIMARY KEY,
    tipo_consulta VARCHAR(100) NOT NULL,
    contexto VARCHAR(100),
    template_resposta TEXT NOT NULL,
    variaveis_necessarias JSONB, -- Que dados precisa
    exemplo_uso TEXT,
    taxa_satisfacao FLOAT DEFAULT 0.5,
    uso_count INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. MÉTRICAS DE APRENDIZADO
CREATE TABLE IF NOT EXISTS ai_learning_metrics (
    id SERIAL PRIMARY KEY,
    metrica_tipo VARCHAR(50) NOT NULL, -- 'accuracy', 'satisfaction', 'performance'
    metrica_valor FLOAT NOT NULL,
    contexto JSONB,
    periodo_inicio TIMESTAMP NOT NULL,
    periodo_fim TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ÍNDICES PARA PERFORMANCE
CREATE INDEX idx_patterns_type_text ON ai_knowledge_patterns(pattern_type, pattern_text);
CREATE INDEX idx_patterns_confidence ON ai_knowledge_patterns(confidence DESC);
CREATE INDEX idx_semantic_termo ON ai_semantic_mappings(termo_usuario);
CREATE INDEX idx_semantic_campo ON ai_semantic_mappings(campo_sistema);
CREATE INDEX idx_learning_created ON ai_learning_history(created_at DESC);
CREATE INDEX idx_grupos_ativo ON ai_grupos_empresariais(ativo) WHERE ativo = TRUE;
CREATE INDEX idx_grupos_cnpj ON ai_grupos_empresariais USING GIN(cnpj_prefixos);
CREATE INDEX idx_business_ativo ON ai_business_contexts(ativo) WHERE ativo = TRUE;
CREATE INDEX idx_templates_tipo ON ai_response_templates(tipo_consulta);

-- TRIGGERS PARA ATUALIZAÇÃO AUTOMÁTICA
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_patterns_timestamp 
    BEFORE UPDATE ON ai_knowledge_patterns 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_grupos_timestamp 
    BEFORE UPDATE ON ai_grupos_empresariais 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_contexts_timestamp 
    BEFORE UPDATE ON ai_business_contexts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- VIEWS ÚTEIS
CREATE OR REPLACE VIEW ai_top_patterns AS
SELECT 
    pattern_type,
    pattern_text,
    interpretation,
    confidence,
    usage_count,
    success_rate,
    confidence * success_rate * LOG(usage_count + 1) as score
FROM ai_knowledge_patterns
WHERE confidence > 0.3
ORDER BY score DESC;

CREATE OR REPLACE VIEW ai_grupos_ativos AS
SELECT 
    nome_grupo,
    tipo_negocio,
    cnpj_prefixos,
    palavras_chave,
    filtro_sql,
    estatisticas
FROM ai_grupos_empresariais
WHERE ativo = TRUE
ORDER BY nome_grupo;

-- COMENTÁRIOS EXPLICATIVOS
COMMENT ON TABLE ai_knowledge_patterns IS 'Padrões de consulta aprendidos pelo sistema';
COMMENT ON TABLE ai_semantic_mappings IS 'Mapeamento entre termos do usuário e campos do sistema';
COMMENT ON TABLE ai_learning_history IS 'Histórico completo de aprendizado com correções';
COMMENT ON TABLE ai_grupos_empresariais IS 'Grupos empresariais detectados e aprendidos';
COMMENT ON TABLE ai_business_contexts IS 'Contextos de negócio e regras aprendidas';
COMMENT ON TABLE ai_response_templates IS 'Templates de resposta que funcionaram bem';
COMMENT ON TABLE ai_learning_metrics IS 'Métricas de performance do aprendizado'; 