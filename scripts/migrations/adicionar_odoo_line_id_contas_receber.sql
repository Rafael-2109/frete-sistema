-- Adicionar odoo_line_id (account.move.line ID) à tabela contas_a_receber
-- Alinha com o padrão já existente em contas_a_pagar
-- Data: 21/02/2026

ALTER TABLE contas_a_receber ADD COLUMN IF NOT EXISTS odoo_line_id INTEGER NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_contas_a_receber_odoo_line_id ON contas_a_receber(odoo_line_id);
