-- F5 PAD-CTX (2026-06-09): proveniencia + frescor em agent_memories.
-- Plano: docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md FASE 5
-- Padrao: .claude/references/ARQUITETURA_CONTEXTO_AGENTE.md secao "Memorias".
-- Idempotente (IF NOT EXISTS) — seguro para Render Shell.

ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS source_session_id TEXT;
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS last_confirmed TIMESTAMP;
ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS confidence TEXT;

CREATE INDEX IF NOT EXISTS ix_agent_memories_source_session_id
    ON agent_memories (source_session_id);

-- NOTA: sem ';' DENTRO das strings — o runner .py faz split por ';'.
COMMENT ON COLUMN agent_memories.source_session_id IS
    'Sessao que ORIGINOU a memoria (imutavel / NULL = legado ou daemon sem sessao). '
    'Exposicao na injecao e cross-user-safe: pessoal -> session= / empresa -> apenas created_by+date.';
COMMENT ON COLUMN agent_memories.last_confirmed IS
    'Ultima (re)confirmacao do conteudo — create e updates renovam. '
    'Correcao nova SEMPRE prevalece sobre memoria antiga em conflito (PAD-CTX).';
COMMENT ON COLUMN agent_memories.confidence IS
    'Confianca declarada da memoria (NULL = nao avaliada). Consumo: F5.5+/F6 do plano PAD-CTX.';
