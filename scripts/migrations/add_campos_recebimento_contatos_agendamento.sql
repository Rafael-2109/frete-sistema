-- Migration: Adicionar campos de horário e observações de recebimento em contatos_agendamento
-- Data: 2026-03-11
-- Autor: Sistema

ALTER TABLE contatos_agendamento ADD COLUMN IF NOT EXISTS horario_recebimento_de TIME;
ALTER TABLE contatos_agendamento ADD COLUMN IF NOT EXISTS horario_recebimento_ate TIME;
ALTER TABLE contatos_agendamento ADD COLUMN IF NOT EXISTS observacoes_recebimento TEXT;
