-- Migration v17 (2026-05-25): UK em RecebimentoLf.odoo_lf_invoice_id
-- Origem: CRITICAL-3 reviewer 2 do Skill 8 ETAPA E.
--
-- Garante idempotencia (G-RECLF-3 do PLANEJAMENTO_SKILL8_FATURANDO.md):
-- duas chamadas concorrentes (ou re-entrada apos crash) NAO podem criar 2
-- RecebimentoLf para a mesma invoice da LF — svc.processar_recebimento
-- executaria a mesma NF duas vezes no Odoo (PO/Picking/Invoice duplicado).
--
-- Pre-flight v17 (PROD 2026-05-25): zero duplicatas detectadas em
-- INVENTARIO_2026_05 (7 NULLs aceitos por padrao do Postgres).
--
-- Idempotente (DO $$ BEGIN ... EXCEPTION ... END $$ duplicate_object).

DO $$
BEGIN
    ALTER TABLE recebimento_lf
        ADD CONSTRAINT uq_recebimento_lf_invoice_id
        UNIQUE (odoo_lf_invoice_id);
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Constraint uq_recebimento_lf_invoice_id ja existe — skip.';
    WHEN duplicate_table THEN
        RAISE NOTICE 'Constraint uq_recebimento_lf_invoice_id ja existe — skip.';
END
$$;
