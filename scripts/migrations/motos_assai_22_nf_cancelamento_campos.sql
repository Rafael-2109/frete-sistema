-- Migration 22: 3 colunas de auditoria de cancelamento de NF.
-- D3 + R5 + S15.

BEGIN;

ALTER TABLE assai_nf_qpa
    ADD COLUMN IF NOT EXISTS cancelada_em TIMESTAMP,
    ADD COLUMN IF NOT EXISTS cancelada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;

CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_cancelada
    ON assai_nf_qpa(cancelada_em DESC) WHERE cancelada_em IS NOT NULL;

COMMIT;
