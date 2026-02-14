-- Migration: Antecipar Recebimento LF
-- Adiciona campo odoo_lf_invoice_id e torna odoo_dfe_id nullable
-- Idempotente: seguro para executar multiplas vezes

-- 1. Novo campo: invoice da LF (fluxo antecipado)
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_lf_invoice_id INTEGER;

-- 2. Indice para busca por lf_invoice_id
CREATE INDEX IF NOT EXISTS ix_recebimento_lf_odoo_lf_invoice_id
    ON recebimento_lf (odoo_lf_invoice_id);

-- 3. Tornar odoo_dfe_id nullable (DFe pode ser criado em step 0)
ALTER TABLE recebimento_lf ALTER COLUMN odoo_dfe_id DROP NOT NULL;

-- Verificacao
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_name = 'recebimento_lf'
  AND column_name IN ('odoo_dfe_id', 'odoo_lf_invoice_id')
ORDER BY column_name;
