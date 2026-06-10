-- Migration: entrega proativa Teams (plano 2026-06-10-teams-melhorias, Fase C)
-- 1. teams_tasks.conversation_reference -> ConversationReference serializado do
--    Bot Framework (permite continue_conversation apos o polling morrer)
-- 2. teams_tasks.delivered_via -> claim atomico de entrega ('polling'|'proactive')
-- Idempotente: pode rodar 2x sem efeito.

ALTER TABLE teams_tasks ADD COLUMN IF NOT EXISTS conversation_reference JSONB;
ALTER TABLE teams_tasks ADD COLUMN IF NOT EXISTS delivered_via VARCHAR(12);
