-- Migration: placeholder em carvia_cotacao_motos + cadastro_pendente em carvia_modelos_moto
-- Idempotente (IF NOT EXISTS). Suporta cadastro tardio de modelo trazido por NF.

ALTER TABLE carvia_cotacao_motos
    ADD COLUMN IF NOT EXISTS placeholder BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE carvia_modelos_moto
    ADD COLUMN IF NOT EXISTS cadastro_pendente BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_motos_placeholder
    ON carvia_cotacao_motos (cotacao_id)
    WHERE placeholder = TRUE;

CREATE INDEX IF NOT EXISTS ix_carvia_modelos_moto_cadastro_pendente
    ON carvia_modelos_moto (id)
    WHERE cadastro_pendente = TRUE;
