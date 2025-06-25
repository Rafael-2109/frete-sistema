-- SISTEMA AVANCADO DE IA - ESTRUTURA POSTGRESQL + JSONB
-- Script para criar tabelas necessarias para todas as funcionalidades avancadas

-- Tabela principal para sessoes avancadas de IA
CREATE TABLE IF NOT EXISTS ai_advanced_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Indices para performance em consultas JSONB
CREATE INDEX IF NOT EXISTS idx_ai_sessions_metadata_gin 
ON ai_advanced_sessions USING gin(metadata_jsonb);

CREATE INDEX IF NOT EXISTS idx_ai_sessions_user_date 
ON ai_advanced_sessions(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_ai_sessions_domain 
ON ai_advanced_sessions USING gin((metadata_jsonb->'session_tags'->>'domain'));

CREATE INDEX IF NOT EXISTS idx_ai_sessions_confidence 
ON ai_advanced_sessions USING gin((metadata_jsonb->'metacognitive'->>'confidence_score'));

-- Tabela para historico de feedback e learning
CREATE TABLE IF NOT EXISTS ai_feedback_history (
    feedback_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) REFERENCES ai_advanced_sessions(session_id),
    user_id INTEGER REFERENCES usuarios(id),
    query_original TEXT NOT NULL,
    response_original TEXT NOT NULL,
    feedback_text TEXT NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    applied BOOLEAN DEFAULT FALSE,
    context_jsonb JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_feedback_user_date 
ON ai_feedback_history(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_feedback_type_severity 
ON ai_feedback_history(feedback_type, severity);

CREATE INDEX IF NOT EXISTS idx_feedback_processed 
ON ai_feedback_history(processed, applied);

-- Tabela para padroes de aprendizado identificados
CREATE TABLE IF NOT EXISTS ai_learning_patterns (
    pattern_id VARCHAR(50) PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    confidence_score DECIMAL(3,2) DEFAULT 0.5,
    improvement_suggestion TEXT,
    examples_jsonb JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_patterns_type_confidence 
ON ai_learning_patterns(pattern_type, confidence_score);

CREATE INDEX IF NOT EXISTS idx_patterns_frequency 
ON ai_learning_patterns(frequency DESC);

-- Tabela para metricas de performance do sistema
CREATE TABLE IF NOT EXISTS ai_performance_metrics (
    metric_id SERIAL PRIMARY KEY,
    metric_date DATE DEFAULT CURRENT_DATE,
    metric_type VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    metadata_jsonb JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metrics_date_type 
ON ai_performance_metrics(metric_date, metric_type);

-- Tabela para cache de embeddings semanticos (futuro FAISS)
CREATE TABLE IF NOT EXISTS ai_semantic_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    content_text TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    embedding_vector JSONB,
    model_version VARCHAR(20) DEFAULT 'v1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embeddings_hash 
ON ai_semantic_embeddings(content_hash);

CREATE INDEX IF NOT EXISTS idx_embeddings_type 
ON ai_semantic_embeddings(content_type);

-- Tabela para configuracoes e preferencias do sistema
CREATE TABLE IF NOT EXISTS ai_system_config (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value JSONB NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir configuracoes padrao
INSERT INTO ai_system_config (config_key, config_value, description) VALUES
('multi_agent_enabled', 'true'::jsonb, 'Habilitar sistema multi-agente'),
('human_learning_enabled', 'true'::jsonb, 'Habilitar aprendizado humano'),
('semantic_loop_max_iterations', '3'::jsonb, 'Maximo de iteracoes do loop semantico'),
('metacognitive_threshold', '0.7'::jsonb, 'Threshold para analise metacognitiva'),
('auto_tagging_enabled', 'true'::jsonb, 'Habilitar auto-tagging de sessoes'),
('advanced_analytics_retention_days', '90'::jsonb, 'Dias para manter analytics avancadas')
ON CONFLICT (config_key) DO NOTHING;

-- View para analises rapidas
CREATE OR REPLACE VIEW ai_session_analytics AS
SELECT 
    DATE(created_at) as session_date,
    COUNT(*) as total_sessions,
    COUNT(DISTINCT user_id) as unique_users,
    AVG((metadata_jsonb->'metacognitive'->>'confidence_score')::decimal) as avg_confidence,
    COUNT(*) FILTER (WHERE metadata_jsonb->'session_tags'->>'confidence' = 'high') as high_confidence_sessions,
    COUNT(*) FILTER (WHERE metadata_jsonb->'session_tags'->>'complexity' = 'high') as complex_sessions,
    COUNT(*) FILTER (WHERE metadata_jsonb->'semantic_loop'->'semantic_refinements' IS NOT NULL) as refined_sessions
FROM ai_advanced_sessions
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY session_date DESC;

-- View para feedback analytics
CREATE OR REPLACE VIEW ai_feedback_analytics AS
SELECT 
    DATE(created_at) as feedback_date,
    feedback_type,
    severity,
    COUNT(*) as feedback_count,
    COUNT(*) FILTER (WHERE processed = true) as processed_count,
    COUNT(*) FILTER (WHERE applied = true) as applied_count
FROM ai_feedback_history
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), feedback_type, severity
ORDER BY feedback_date DESC, feedback_count DESC;

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ai_sessions_updated_at 
    BEFORE UPDATE ON ai_advanced_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_patterns_updated_at 
    BEFORE UPDATE ON ai_learning_patterns 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_config_updated_at 
    BEFORE UPDATE ON ai_system_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 