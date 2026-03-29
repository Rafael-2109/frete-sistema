-- Migration: Tabela scheduler_health para monitoramento de saude do scheduler
-- Data: 2026-03-29

CREATE TABLE IF NOT EXISTS scheduler_health (
    id SERIAL PRIMARY KEY,
    step_name VARCHAR(100) NOT NULL,
    step_number INTEGER NOT NULL,
    executado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL,  -- OK, ERRO, SKIP
    duracao_ms INTEGER,
    erro TEXT,
    detalhes TEXT
);

CREATE INDEX IF NOT EXISTS idx_sh_step_name ON scheduler_health (step_name);
CREATE INDEX IF NOT EXISTS idx_sh_executado_em ON scheduler_health (executado_em);
