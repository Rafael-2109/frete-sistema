-- Migration: Adicionar campo criacao_tardia em carvia_cotacoes
-- Idempotente: usa IF NOT EXISTS
-- Execucao: Render Shell > psql

ALTER TABLE carvia_cotacoes
ADD COLUMN IF NOT EXISTS criacao_tardia BOOLEAN NOT NULL DEFAULT FALSE;
