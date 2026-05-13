-- Migration 27: UNIQUE parcial em assai_nf_qpa(separacao_id) WHERE status_match != 'CANCELADA'.
-- A3 — garante apenas 1 NF ativa por sep.
-- Cenario: Sep nasce FATURADA com NF A; NF A cancelada; NF B chega para a mesma sep.

BEGIN;

-- Validacao: verificar que nao ha violacoes ANTES de aplicar
DO $$
DECLARE
    violacoes INTEGER;
BEGIN
    SELECT COUNT(*) INTO violacoes FROM (
        SELECT separacao_id, COUNT(*) AS qty
        FROM assai_nf_qpa
        WHERE separacao_id IS NOT NULL
          AND status_match != 'CANCELADA'
        GROUP BY separacao_id
        HAVING COUNT(*) > 1
    ) sub;

    IF violacoes > 0 THEN
        RAISE EXCEPTION 'Violacao: % seps com >1 NF ativa. Resolver antes de aplicar UNIQUE.', violacoes;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_nf_qpa_separacao_ativa
    ON assai_nf_qpa(separacao_id)
    WHERE separacao_id IS NOT NULL AND status_match != 'CANCELADA';

COMMIT;
