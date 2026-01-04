-- Migração: Adicionar campo nao_aceita_nf_pallet
-- Data: 02/01/2026
-- Executar no Shell do Render

-- 1. Tabela contatos_agendamento (clientes)
ALTER TABLE contatos_agendamento
ADD COLUMN IF NOT EXISTS nao_aceita_nf_pallet BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Tabela transportadoras
ALTER TABLE transportadoras
ADD COLUMN IF NOT EXISTS nao_aceita_nf_pallet BOOLEAN NOT NULL DEFAULT FALSE;
