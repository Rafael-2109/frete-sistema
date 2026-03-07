-- Migration: Remover coluna is_permanent de agent_memories
-- S6: Dead Code Cleanup — campo 100% redundante com category == 'permanent'
--
-- Executar no Render Shell (PostgreSQL).
-- Idempotente: IF EXISTS evita erro se já removida.

-- Verificação BEFORE (executar manualmente, confirmar 0 em ambos):
-- SELECT count(*) FROM agent_memories WHERE is_permanent = true AND category != 'permanent';
-- SELECT count(*) FROM agent_memories WHERE is_permanent = false AND category = 'permanent';

-- Execute:
ALTER TABLE agent_memories DROP COLUMN IF EXISTS is_permanent;

-- Verificação AFTER:
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'agent_memories' AND column_name = 'is_permanent';
-- Esperado: 0 rows
