-- Migration 2026-05-28: adiciona 3 colunas em_transito_fb/cd/lf em inventario_snapshot_odoo.
--
-- Captura estoque "escondido" em NFs inter-company emitidas mas ainda nao escrituradas
-- no destino (transit locations 6 e 26489 do Odoo). Quebra por empresa de DESTINO.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS (Postgres 9.6+).

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS em_transito_fb NUMERIC(15, 3) DEFAULT 0;

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS em_transito_cd NUMERIC(15, 3) DEFAULT 0;

ALTER TABLE inventario_snapshot_odoo
    ADD COLUMN IF NOT EXISTS em_transito_lf NUMERIC(15, 3) DEFAULT 0;
