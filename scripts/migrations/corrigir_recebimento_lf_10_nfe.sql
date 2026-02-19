-- Correcao RecebimentoLf ID 10 — Diagnostico (2026-02-18)
-- Sem DDL — apenas queries de diagnostico

-- Estado atual do recebimento
SELECT id, status, etapa_atual, transfer_status, transfer_erro_mensagem,
       odoo_transfer_invoice_id, odoo_transfer_invoice_name,
       odoo_transfer_out_picking_id, odoo_dfe_id,
       erro_mensagem, ultimo_checkpoint_em, job_id
FROM recebimento_lf
WHERE id = 10;

-- Estado de todos os LF para contexto
SELECT id, status, etapa_atual, transfer_status,
       odoo_transfer_invoice_name, ultimo_checkpoint_em
FROM recebimento_lf
ORDER BY id;
