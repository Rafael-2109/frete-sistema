-- =============================================================
-- MIGRAÇÃO: Campos de Impostos e Desconto Contratual
-- Tabela: carteira_principal
-- Data: 2025-12-26
-- =============================================================

-- Campos de impostos da linha (sale.order.line)
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS icms_valor NUMERIC(15, 2) NULL;
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS icmsst_valor NUMERIC(15, 2) NULL;
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS pis_valor NUMERIC(15, 2) NULL;
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS cofins_valor NUMERIC(15, 2) NULL;

-- Campos de desconto contratual do cliente (res.partner)
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS desconto_contratual BOOLEAN DEFAULT FALSE;
ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS desconto_percentual NUMERIC(5, 2) NULL;

-- Comentários para documentação
COMMENT ON COLUMN carteira_principal.icms_valor IS 'Valor do ICMS da linha (l10n_br_icms_valor)';
COMMENT ON COLUMN carteira_principal.icmsst_valor IS 'Valor do ICMS ST da linha (l10n_br_icmsst_valor)';
COMMENT ON COLUMN carteira_principal.pis_valor IS 'Valor do PIS da linha (l10n_br_pis_valor)';
COMMENT ON COLUMN carteira_principal.cofins_valor IS 'Valor do COFINS da linha (l10n_br_cofins_valor)';
COMMENT ON COLUMN carteira_principal.desconto_contratual IS 'Flag se cliente tem desconto contratual (x_studio_desconto_contratual)';
COMMENT ON COLUMN carteira_principal.desconto_percentual IS 'Percentual de desconto contratual (x_studio_desconto)';

-- Verificar colunas criadas
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'carteira_principal'
AND column_name IN ('icms_valor', 'icmsst_valor', 'pis_valor', 'cofins_valor', 'desconto_contratual', 'desconto_percentual')
ORDER BY ordinal_position;
