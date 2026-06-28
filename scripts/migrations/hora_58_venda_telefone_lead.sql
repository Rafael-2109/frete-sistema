-- Idempotente. Adiciona telefone_lead (VARCHAR(20), NULL) a hora_venda.
-- Telefone do LEAD (contato original que originou a venda), distinto do
-- telefone do destinatario fiscal (telefone_cliente). Registro/exibicao
-- apenas — NAO entra no payload da NFe.
-- Migration HORA 58 (2026-06-28).
ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS telefone_lead VARCHAR(20);
