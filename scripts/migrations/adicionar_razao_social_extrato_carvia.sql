-- Migration: Adicionar razao_social e observacao em carvia_extrato_linhas
-- Idempotente — seguro para re-executar no Render Shell

ALTER TABLE carvia_extrato_linhas ADD COLUMN IF NOT EXISTS razao_social VARCHAR(255);
ALTER TABLE carvia_extrato_linhas ADD COLUMN IF NOT EXISTS observacao TEXT;
