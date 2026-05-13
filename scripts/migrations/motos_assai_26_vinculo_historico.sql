-- Migration 26: assai_nf_qpa_item_vinculo_historico.
-- S16=c — auditoria de vinculo NF-item ↔ Sep-item antes de cancelamento.

BEGIN;

CREATE TABLE IF NOT EXISTS assai_nf_qpa_item_vinculo_historico (
    id SERIAL PRIMARY KEY,
    nf_qpa_item_id INTEGER NOT NULL REFERENCES assai_nf_qpa_item(id),
    separacao_item_id INTEGER REFERENCES assai_separacao_item(id) ON DELETE SET NULL,
    motivo VARCHAR(40) NOT NULL,
    chassi_no_momento VARCHAR(50) NOT NULL,
    registrado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    registrado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    detalhes JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo
        CHECK (motivo IN ('NF_CANCELADA', 'CCE_ALTEROU_CHASSI', 'SUBSTITUICAO_CROSS_LOJA'))
);

CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_vinculo_hist_nf
    ON assai_nf_qpa_item_vinculo_historico(nf_qpa_item_id);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_vinculo_hist_sep
    ON assai_nf_qpa_item_vinculo_historico(separacao_item_id) WHERE separacao_item_id IS NOT NULL;

COMMIT;
