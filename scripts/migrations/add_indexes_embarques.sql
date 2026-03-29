-- Migration: Indexes de performance para embarques e embarque_itens
-- Tabelas sem indexes customizados, usadas em joins frequentes
-- Data: 2026-03-29

-- embarques
CREATE INDEX IF NOT EXISTS idx_emb_status ON embarques (status);
CREATE INDEX IF NOT EXISTS idx_emb_data_embarque ON embarques (data_embarque);
CREATE INDEX IF NOT EXISTS idx_emb_transportadora_status ON embarques (transportadora_id, status);
CREATE INDEX IF NOT EXISTS idx_emb_tipo_carga ON embarques (tipo_carga);

-- embarque_itens
CREATE INDEX IF NOT EXISTS idx_ei_embarque_status ON embarque_itens (embarque_id, status);
CREATE INDEX IF NOT EXISTS idx_ei_nota_fiscal ON embarque_itens (nota_fiscal);
CREATE INDEX IF NOT EXISTS idx_ei_cnpj_cliente ON embarque_itens (cnpj_cliente);
CREATE INDEX IF NOT EXISTS idx_ei_uf_destino ON embarque_itens (uf_destino);

-- Atualizar estatisticas
ANALYZE embarques;
ANALYZE embarque_itens;
