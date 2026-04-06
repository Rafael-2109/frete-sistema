-- Migration: Adicionar arquivo_path e fornecedor em frota_despesas
-- Data: 2026-04-06
-- Idempotente: sim (IF NOT EXISTS)

ALTER TABLE frota_despesas ADD COLUMN IF NOT EXISTS arquivo_path VARCHAR(500);
ALTER TABLE frota_despesas ADD COLUMN IF NOT EXISTS fornecedor VARCHAR(150);
