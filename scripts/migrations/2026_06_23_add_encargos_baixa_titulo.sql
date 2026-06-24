-- 2026-06-23: colunas de ENCARGOS na baixa de titulos por template (antecipacao Sendas/Assai)
-- Idempotente (IF NOT EXISTS) — seguro para Render Shell / DATABASE_URL_PROD.
--
-- encargos_excel: valor de encargo financeiro informado na planilha (sanity check;
--   o write-off real = saldo - liquido, lancado na conta ENCARGOS DE EMPRESTIMOS E FINANCIAMENTOS).
-- payment_encargos_odoo_id/name: referencia ao write-off (mesmo account.payment do liquido).

ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS encargos_excel DOUBLE PRECISION DEFAULT 0;
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_encargos_odoo_id INTEGER;
ALTER TABLE baixa_titulo_item ADD COLUMN IF NOT EXISTS payment_encargos_odoo_name VARCHAR(100);
