-- Migration HORA 36: campo `consumidor_final` (Boolean) em hora_venda
--
-- Objetivo: permitir que o operador escolha (ou sobreponha o default
-- inferido) se o destinatario da NF-e e consumidor final ou nao. Campo
-- BOOLEAN nullable: NULL significa "nao informado pelo operador" e o
-- payload_builder do TagPlus infere a partir do tipo do documento (CPF=True,
-- CNPJ=False).
--
-- Por que nullable + default NULL:
--   - Vendas legadas (DANFE PDF importado) nao tinham UI para o campo.
--     Mantemos NULL para que o payload_builder aplique a inferencia
--     quando/se a venda for re-emitida (raramente).
--   - Vendas novas (criadas via /tagplus/pedido-venda/novo) sempre vao
--     gravar TRUE/FALSE explicito porque o checkbox no formulario tem
--     default inferido client-side e e enviado no submit.
--
-- Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS consumidor_final BOOLEAN;
