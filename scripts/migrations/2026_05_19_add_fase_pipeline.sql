-- Migration: adiciona campos fase_pipeline + picking_id_odoo + invoice_id_odoo + chave_nfe
-- em ajuste_estoque_inventario, e pipeline_etapa em operacao_odoo_auditoria.
-- Motivo: D003 (pipeline em batches) apos G004 (padrao real eh picking+robo+Playwright).

BEGIN;

-- ajuste_estoque_inventario: campos de pipeline
ALTER TABLE ajuste_estoque_inventario
    ADD COLUMN IF NOT EXISTS fase_pipeline VARCHAR(20),
    ADD COLUMN IF NOT EXISTS picking_id_odoo INTEGER,
    ADD COLUMN IF NOT EXISTS invoice_id_odoo INTEGER,
    ADD COLUMN IF NOT EXISTS chave_nfe VARCHAR(44);

CREATE INDEX IF NOT EXISTS idx_aei_fase_pipeline ON ajuste_estoque_inventario (fase_pipeline);

-- operacao_odoo_auditoria: pipeline_etapa para rastreabilidade
ALTER TABLE operacao_odoo_auditoria
    ADD COLUMN IF NOT EXISTS pipeline_etapa VARCHAR(20);

COMMIT;
