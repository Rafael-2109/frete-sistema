-- Migration: Adicionar campos de favorecido ao extrato_item
-- Data: 2026-02-11
-- Descricao: 8 novas colunas para resolver favorecido em pagamentos de saida
-- Idempotente: usa IF NOT EXISTS / ADD COLUMN IF NOT EXISTS

-- =========================================================================
-- DADOS DO PARCEIRO ODOO (capturados na importacao)
-- =========================================================================

ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS odoo_partner_id INTEGER;
ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS odoo_partner_name VARCHAR(255);
ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS odoo_partner_cnpj VARCHAR(20);

-- =========================================================================
-- FAVORECIDO RESOLVIDO (preenchido pelo pipeline)
-- =========================================================================

ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS favorecido_cnpj VARCHAR(20);
ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS favorecido_nome VARCHAR(255);
ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS favorecido_metodo VARCHAR(30);
ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS favorecido_confianca INTEGER;
ALTER TABLE extrato_item ADD COLUMN IF NOT EXISTS categoria_pagamento VARCHAR(30);

-- =========================================================================
-- INDICES
-- =========================================================================

CREATE INDEX IF NOT EXISTS idx_extrato_item_favorecido_cnpj
    ON extrato_item (favorecido_cnpj);

CREATE INDEX IF NOT EXISTS idx_extrato_item_categoria_pag
    ON extrato_item (categoria_pagamento);

CREATE INDEX IF NOT EXISTS idx_extrato_item_odoo_partner
    ON extrato_item (odoo_partner_id);
