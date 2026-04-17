-- Migration: adicionar coluna priority em agent_memories
-- Ref: docs/superpowers/plans/2026-04-16-memory-system-redesign.md Task 2
-- Data: 2026-04-16

BEGIN;

ALTER TABLE agent_memories
  ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'contextual';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agent_memories_priority_check') THEN
    ALTER TABLE agent_memories
      ADD CONSTRAINT agent_memories_priority_check
      CHECK (priority IN ('mandatory', 'advisory', 'contextual'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_agent_memories_mandatory
  ON agent_memories (user_id, path)
  WHERE priority = 'mandatory' AND is_cold = false;

COMMIT;

SELECT priority, COUNT(*) FROM agent_memories GROUP BY priority;
