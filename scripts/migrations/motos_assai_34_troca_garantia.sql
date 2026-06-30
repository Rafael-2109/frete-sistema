-- Migration 34: Troca em garantia.
-- (1) Estende assai_pos_venda_ocorrencia com tipo/chassi_substituto/nf_qpa_id.
-- (2) Adiciona TROCA_GARANTIA ao CHECK de assai_nf_qpa_item_vinculo_historico.motivo.
-- Padrao idempotente (DROP IF EXISTS + ADD).

BEGIN;

ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'RELATO';
ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS chassi_substituto VARCHAR(50);
ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS nf_qpa_id INTEGER REFERENCES assai_nf_qpa(id);

CREATE INDEX IF NOT EXISTS ix_assai_pos_venda_ocorrencia_nf_qpa_id
    ON assai_pos_venda_ocorrencia (nf_qpa_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_nf_qpa_item_vinculo_motivo') THEN
        ALTER TABLE assai_nf_qpa_item_vinculo_historico DROP CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo;
    END IF;
    ALTER TABLE assai_nf_qpa_item_vinculo_historico
        ADD CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo
        CHECK (motivo IN (
            'NF_CANCELADA', 'CCE_ALTEROU_CHASSI', 'SUBSTITUICAO_CROSS_LOJA',
            'TROCA_GARANTIA'
        ));
END $$;

COMMIT;
