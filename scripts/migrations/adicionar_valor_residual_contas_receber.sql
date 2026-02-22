-- Migration: Adicionar valor_residual em contas_a_receber
-- Alinha com padrão existente em contas_a_pagar
-- Data: 21/02/2026

ALTER TABLE contas_a_receber ADD COLUMN IF NOT EXISTS valor_residual FLOAT NULL;
