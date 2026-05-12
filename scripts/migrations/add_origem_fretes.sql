-- Migration: adicionar fretes.origem (NACOM | OP_ASSAI)
-- Data: 2026-05-11
-- Descricao: Identifica origem do frete para flag visivel em Lancamento Freteiros,
--   exportacao de fechamento e relatorios. Default 'NACOM' preserva fretes existentes.
-- Idempotente: usa IF NOT EXISTS + checagem de constraint.

ALTER TABLE fretes ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'NACOM';

CREATE INDEX IF NOT EXISTS idx_fretes_origem ON fretes (origem);
