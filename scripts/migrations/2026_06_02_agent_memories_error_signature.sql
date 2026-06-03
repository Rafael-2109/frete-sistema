-- scripts/migrations/2026_06_02_agent_memories_error_signature.sql
-- Fase 3 (loop corretivo): medicao POR OUTCOME + assinatura de erro em agent_memories.
-- error_signature = hash de intencao normalizada (casa reincidencia entre sessoes);
-- harmful_count = regra mandatory injetada e o erro reincidiu mesmo assim (falhou);
-- helpful_count = regra mandatory injetada e sem reincidencia por K sessoes (funcionou).
-- Desacoplado de effective_count (eco textual, so dashboard). Idempotente (Render Shell).
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS error_signature VARCHAR(64);
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS harmful_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS helpful_count INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS ix_agent_memories_user_errsig
    ON agent_memories (user_id, error_signature);
