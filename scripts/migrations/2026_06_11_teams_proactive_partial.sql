-- Migration: blocos proativos pos-polling Teams (plano 2026-06-10-teams-melhorias, Fase E2)
-- teams_tasks.proactive_partial_chars -> offset de chars da resposta ja entregues
-- via blocos proativos (mensagens novas pos-polling). A entrega FINAL envia apenas
-- resposta[proactive_partial_chars:]. Offset 0 = comportamento anterior (resposta completa).
-- Idempotente: pode rodar 2x sem efeito.

ALTER TABLE teams_tasks ADD COLUMN IF NOT EXISTS proactive_partial_chars INTEGER NOT NULL DEFAULT 0;
