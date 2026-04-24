-- Migration: Adicionar coluna `preferences` JSONB em usuarios
-- Data: 2026-04-23
-- Motivo: Persistir preferencias per-user do Agente Logistico Web
--         (primeira preferencia: agent_thinking_display).
-- Idempotente: IF NOT EXISTS.

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS preferences JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Sem index: consultas sao per-user-id (PK ja indexado). Coluna e acessada
-- apenas como payload via SELECT preferences FROM usuarios WHERE id = :id.
