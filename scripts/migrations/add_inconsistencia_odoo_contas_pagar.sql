-- Migration: Adiciona campos de inconsistencia Odoo em contas_a_pagar
-- Executar via Render Shell (SQL idempotente)
--
-- Campos:
--   inconsistencia_odoo: tipo da inconsistencia (PAGO_LOCAL_ABERTO_ODOO, etc.)
--   inconsistencia_detectada_em: timestamp de quando foi detectada
--   inconsistencia_resolvida_em: timestamp de quando foi resolvida
--
-- Valores possiveis de inconsistencia_odoo:
--   PAGO_LOCAL_ABERTO_ODOO — parcela_paga=True mas Odoo mostra not_paid/partial
--   VALOR_RESIDUAL_DIVERGENTE — valor_residual local != abs(amount_residual) Odoo
--   SEM_MATCH_ODOO — odoo_line_id existe mas nao encontrado no Odoo
--   NULL — Sem inconsistencia

ALTER TABLE contas_a_pagar
    ADD COLUMN IF NOT EXISTS inconsistencia_odoo VARCHAR(50);

ALTER TABLE contas_a_pagar
    ADD COLUMN IF NOT EXISTS inconsistencia_detectada_em TIMESTAMP;

ALTER TABLE contas_a_pagar
    ADD COLUMN IF NOT EXISTS inconsistencia_resolvida_em TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_contas_a_pagar_inconsistencia
    ON contas_a_pagar(inconsistencia_odoo)
    WHERE inconsistencia_odoo IS NOT NULL;
