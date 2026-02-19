-- Migration: Adicionar coluna metodo_baixa em contas_a_receber e contas_a_pagar
-- Rastreabilidade: indica COMO o titulo foi baixado (CNAB, EXCEL, COMPROVANTE, EXTRATO, ODOO_DIRETO)
-- Idempotente: usa IF NOT EXISTS

ALTER TABLE contas_a_receber ADD COLUMN IF NOT EXISTS metodo_baixa VARCHAR(30);
ALTER TABLE contas_a_pagar ADD COLUMN IF NOT EXISTS metodo_baixa VARCHAR(30);

CREATE INDEX IF NOT EXISTS idx_conta_receber_metodo_baixa ON contas_a_receber (metodo_baixa);
CREATE INDEX IF NOT EXISTS idx_conta_pagar_metodo_baixa ON contas_a_pagar (metodo_baixa);
