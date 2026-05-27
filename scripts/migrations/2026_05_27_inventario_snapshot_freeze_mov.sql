-- Migration 2026-05-27: snapshot freeze MOV/SIST em inventario_snapshot_odoo
-- Render Shell: psql $DATABASE_URL -f scripts/migrations/2026_05_27_inventario_snapshot_freeze_mov.sql
-- Idempotente via IF NOT EXISTS.

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS mov_compras NUMERIC(15,3) DEFAULT 0;

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS mov_vendas NUMERIC(15,3) DEFAULT 0;

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS mov_consumo NUMERIC(15,3) DEFAULT 0;

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS mov_producao NUMERIC(15,3) DEFAULT 0;

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS mov_sist_total NUMERIC(15,3) DEFAULT 0;

-- Verificacao pos-migration
SELECT column_name, data_type, numeric_precision, numeric_scale, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'inventario_snapshot_odoo'
  AND column_name IN ('mov_compras', 'mov_vendas', 'mov_consumo',
                       'mov_producao', 'mov_sist_total')
ORDER BY column_name;
