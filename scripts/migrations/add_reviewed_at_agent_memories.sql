-- Migration: Adicionar coluna reviewed_at em agent_memories
-- Objetivo: Ciclo de revisao de memorias (v5)
-- Data: 2026-03-13

ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS idx_agent_memories_reviewed_at
  ON agent_memories (reviewed_at) WHERE reviewed_at IS NULL;
