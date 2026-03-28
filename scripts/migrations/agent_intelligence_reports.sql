-- Migration: agent_intelligence_reports
-- Tabela para persistir relatorios de inteligencia do agente (D7 do cron semanal).
-- Bridge Agent SDK → Claude Code: relatorios com metricas, recomendacoes e backlog.
--
-- Executar via Render Shell:
--   psql $DATABASE_URL -f agent_intelligence_reports.sql

CREATE TABLE IF NOT EXISTS agent_intelligence_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    health_score NUMERIC(5,1) DEFAULT 0,
    friction_score NUMERIC(5,1) DEFAULT 0,
    recommendation_count INTEGER DEFAULT 0,
    sessions_analyzed INTEGER DEFAULT 0,
    report_json JSONB NOT NULL,
    report_markdown TEXT NOT NULL,
    backlog_json JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intelligence_reports_date
    ON agent_intelligence_reports(report_date DESC);

-- Verificacao pos-migration
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'agent_intelligence_reports'
    ) THEN
        RAISE NOTICE 'OK: tabela agent_intelligence_reports criada com sucesso';
    ELSE
        RAISE EXCEPTION 'FALHA: tabela agent_intelligence_reports NAO foi criada';
    END IF;
END $$;
