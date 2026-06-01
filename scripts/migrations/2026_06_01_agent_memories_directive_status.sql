-- scripts/migrations/2026_06_01_agent_memories_directive_status.sql
-- A4: directive_status (candidata|shadow|ativa|despromovida). NULL = memória comum.
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS directive_status VARCHAR(20);
