-- Migration: adiciona observacoes_conferencia em carvia_faturas_transportadora
-- Paridade Nacom: espelha FaturaFrete.observacoes_conferencia usada no fluxo
-- de "Aprovar Conferencia da Fatura".
-- Idempotente: IF NOT EXISTS.

ALTER TABLE carvia_faturas_transportadora
    ADD COLUMN IF NOT EXISTS observacoes_conferencia TEXT NULL;
