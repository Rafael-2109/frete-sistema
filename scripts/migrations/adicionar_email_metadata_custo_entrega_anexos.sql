-- Migration: Adicionar campos de metadados de email em carvia_custo_entrega_anexos
-- Campos nullable — populados apenas para arquivos .msg/.eml

ALTER TABLE carvia_custo_entrega_anexos
    ADD COLUMN IF NOT EXISTS email_remetente VARCHAR(255),
    ADD COLUMN IF NOT EXISTS email_assunto VARCHAR(500),
    ADD COLUMN IF NOT EXISTS email_data_envio TIMESTAMP,
    ADD COLUMN IF NOT EXISTS email_conteudo_preview VARCHAR(500);
