-- Migration HORA 46: origem do lead no pedido de venda (roadmap #6).
-- Como o cliente conheceu a loja (marketing). Idempotente (IF NOT EXISTS).
-- Rodar no Render Shell.
--
-- NAO confundir com hora_venda.origem_criacao (fonte tecnica DANFE/MANUAL).
--   origem_lead     -> canal: GOOGLE / INSTAGRAM / FACEBOOK / OUTROS.
--                      NULL em vendas legadas / import DANFE / backfill.
--   origem_lead_obs -> texto livre; preenchido SO quando origem_lead='OUTROS'.

ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS origem_lead VARCHAR(20);

ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS origem_lead_obs VARCHAR(255);
