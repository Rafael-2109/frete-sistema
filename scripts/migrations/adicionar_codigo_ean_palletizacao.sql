-- Migration: Adicionar campo codigo_ean em cadastro_palletizacao
-- Permite vincular produtos do portal Atacadao (EAN/GTIN) ao cadastro interno
-- Fonte do EAN: Odoo product.template.barcode_nacom
--
-- Execucao: Render Shell (SQL idempotente)
-- Data: 2026-03-08

ALTER TABLE cadastro_palletizacao
    ADD COLUMN IF NOT EXISTS codigo_ean VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_cadastro_palletizacao_ean
    ON cadastro_palletizacao(codigo_ean);

COMMENT ON COLUMN cadastro_palletizacao.codigo_ean
    IS 'Codigo EAN/GTIN do produto. Fonte: Odoo product.template.barcode_nacom';
