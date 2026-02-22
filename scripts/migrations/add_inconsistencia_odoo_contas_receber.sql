-- Migration: Adiciona campos de inconsistência Odoo em contas_a_receber
-- Executar via Render Shell (SQL idempotente)
--
-- Campos:
--   inconsistencia_odoo: tipo da inconsistência (PAGO_LOCAL_ABERTO_ODOO, etc.)
--   inconsistencia_detectada_em: timestamp de quando foi detectada
--   inconsistencia_resolvida_em: timestamp de quando foi resolvida
--
-- Valores possíveis de inconsistencia_odoo:
--   PAGO_LOCAL_ABERTO_ODOO — parcela_paga=True mas Odoo mostra not_paid/partial
--   VALOR_RESIDUAL_DIVERGENTE — valor_residual local ≠ abs(amount_residual) Odoo
--   SEM_MATCH_ODOO — odoo_line_id existe mas não encontrado no Odoo
--   NULL — Sem inconsistência

ALTER TABLE contas_a_receber
    ADD COLUMN IF NOT EXISTS inconsistencia_odoo VARCHAR(50);

ALTER TABLE contas_a_receber
    ADD COLUMN IF NOT EXISTS inconsistencia_detectada_em TIMESTAMP;

ALTER TABLE contas_a_receber
    ADD COLUMN IF NOT EXISTS inconsistencia_resolvida_em TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_contas_a_receber_inconsistencia
    ON contas_a_receber(inconsistencia_odoo)
    WHERE inconsistencia_odoo IS NOT NULL;
