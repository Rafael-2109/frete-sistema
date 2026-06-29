-- Migration: trocar UNIQUE(user_id, path) por UNIQUE(user_id, path, agente) em agent_memories
-- Data: 2026-06-30
-- Motivo: M3/F2 Fase 1 — permitir que web e lojas tenham memória no MESMO path
--         por usuário (ex.: ambos /memories/user.xml), pré-requisito de F3.
-- Uso: Render Shell (psql) — idempotente, pode rodar múltiplas vezes.
-- Seguro: a constraint nova é MENOS restritiva que a antiga; nenhuma linha
--         existente viola (verificado em PROD 2026-06-29: 0 duplicatas (user_id,path),
--         1019 memórias todas agente='web').

BEGIN;

-- 1. Remover a constraint antiga (user_id, path)
ALTER TABLE agent_memories
    DROP CONSTRAINT IF EXISTS uq_user_memory_path;

-- 2. Criar a nova constraint (user_id, path, agente) — idempotente via guard
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_user_memory_path_agente'
    ) THEN
        ALTER TABLE agent_memories
            ADD CONSTRAINT uq_user_memory_path_agente UNIQUE (user_id, path, agente);
    END IF;
END$$;

-- 3. Verificação
SELECT conname
FROM pg_constraint
WHERE conrelid = 'agent_memories'::regclass
  AND contype = 'u';

COMMIT;
