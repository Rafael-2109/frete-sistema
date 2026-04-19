-- Migration HORA 07: adiciona qtd_declarada_itens em hora_nf_entrada
-- Data: 2026-04-19
-- Descricao:
--   Soma da quantidade dos itens de produto (NCM 8711*) extraida do DANFE no momento do import.
--   Usada como gabarito para sinalizar divergencia entre itens declarados x chassis faturados
--   (ex: NF 36928 — item MT-GIGA declarou 1 un mas DANFE lista 2 chassis).
-- Idempotente: ADD COLUMN IF NOT EXISTS.
-- RISCO: baixo. Coluna nullable, sem backfill obrigatorio.

ALTER TABLE hora_nf_entrada
    ADD COLUMN IF NOT EXISTS qtd_declarada_itens INTEGER NULL;
