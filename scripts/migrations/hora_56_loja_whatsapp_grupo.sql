-- Idempotente. Adiciona whatsapp_grupo_jid (JID Baileys "...@g.us") a hora_loja.
-- Requisito "1 grupo por loja": a loja do pedido/NF indica o grupo WhatsApp de
-- destino da notificacao (antes era um unico grupo global por env). Configurado
-- na tela da loja (dropdown dos grupos da Evolution). Migration HORA 56 (2026-06-27).
ALTER TABLE hora_loja ADD COLUMN IF NOT EXISTS whatsapp_grupo_jid VARCHAR(60);
