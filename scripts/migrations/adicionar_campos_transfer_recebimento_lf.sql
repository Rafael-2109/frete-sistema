-- Migration: Adicionar campos de transferencia FB -> CD no Recebimento LF
-- Data: 2026-02-11
-- Contexto: Apos receber NF da LF na FB, transferir produtos acabados para o CD
--
-- Uso: Executar diretamente no Render Shell (SQL idempotente)

-- recebimento_lf: campos de transferencia
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_transfer_out_picking_id INTEGER;
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_transfer_out_picking_name VARCHAR(50);
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_transfer_invoice_id INTEGER;
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_transfer_invoice_name VARCHAR(50);
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_transfer_in_picking_id INTEGER;
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_transfer_in_picking_name VARCHAR(50);
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS transfer_status VARCHAR(20);
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS transfer_erro_mensagem TEXT;

-- recebimento_lf_lote: lot ID no CD
ALTER TABLE recebimento_lf_lote ADD COLUMN IF NOT EXISTS odoo_lot_id_cd INTEGER;

-- Atualizar default total_etapas para novos registros
ALTER TABLE recebimento_lf ALTER COLUMN total_etapas SET DEFAULT 26;

-- Registros pendentes: atualizar total para incluir fase de transferencia
UPDATE recebimento_lf SET total_etapas = 26 WHERE status = 'pendente' AND total_etapas = 18;
