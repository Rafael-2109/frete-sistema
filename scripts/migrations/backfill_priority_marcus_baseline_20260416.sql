-- Migration: backfill priority em memorias criticas do Marcus + baseline.
-- Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md Task 10
-- Data: 2026-04-16
-- Depende de: add_priority_agent_memories.py (coluna priority deve existir).

BEGIN;

-- 1. preferences.xml do Marcus -> mandatory
UPDATE agent_memories
SET priority = 'mandatory'
WHERE user_id = 18
  AND path = '/memories/preferences.xml'
  AND priority <> 'mandatory';

-- 2. user.xml do Marcus -> advisory (sempre injetado mas nao regra)
UPDATE agent_memories
SET priority = 'advisory'
WHERE user_id = 18
  AND path = '/memories/user.xml'
  AND priority <> 'advisory';

-- 3. Heuristica baseline promovida -> mandatory (alta criticidade)
UPDATE agent_memories
SET priority = 'mandatory'
WHERE path LIKE '/memories/empresa/heuristicas/financeiro/baseline-de-extratos%'
  AND priority <> 'mandatory';

-- 4. Heuristicas/protocolos empresa com importance>=0.7 -> advisory (promocao)
UPDATE agent_memories
SET priority = 'advisory'
WHERE user_id = 0
  AND (path LIKE '/memories/empresa/heuristicas/%'
       OR path LIKE '/memories/empresa/protocolos/%')
  AND importance_score >= 0.7
  AND priority = 'contextual';

COMMIT;

-- Verificacao pos-migration
SELECT priority, COUNT(*) AS total
FROM agent_memories
GROUP BY priority
ORDER BY priority;
