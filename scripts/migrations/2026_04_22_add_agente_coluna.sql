-- Migration: Adicionar coluna `agente` em agent_sessions e agent_memories
-- Data: 2026-04-22
-- Motivo: Particionar sessões e memórias entre agente logístico (web) e agente Lojas HORA
-- Uso: Render Shell (psql) — SQL idempotente, pode rodar multiplas vezes

BEGIN;

-- =====================================================================
-- 1. agent_sessions.agente
-- =====================================================================
ALTER TABLE agent_sessions
    ADD COLUMN IF NOT EXISTS agente VARCHAR(20) NOT NULL DEFAULT 'web';

-- Index para list_for_user filtrar eficientemente
CREATE INDEX IF NOT EXISTS ix_agent_sessions_agente_user
    ON agent_sessions (agente, user_id);

-- =====================================================================
-- 2. agent_memories.agente
-- =====================================================================
ALTER TABLE agent_memories
    ADD COLUMN IF NOT EXISTS agente VARCHAR(20) NOT NULL DEFAULT 'web';

-- Index composto (agente + user_id) para retrieval isolado por agente
CREATE INDEX IF NOT EXISTS ix_agent_memories_agente_user
    ON agent_memories (agente, user_id);

-- =====================================================================
-- Verificacao
-- =====================================================================
SELECT
    'agent_sessions' AS tabela,
    agente,
    COUNT(*) AS total
FROM agent_sessions
GROUP BY agente
UNION ALL
SELECT
    'agent_memories' AS tabela,
    agente,
    COUNT(*) AS total
FROM agent_memories
GROUP BY agente
ORDER BY tabela, agente;

COMMIT;
