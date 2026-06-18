-- Migration: Recebimento por chassi da Coleta CarVia — stream 4 do redesign
-- Data: 2026-06-17
-- Descricao:
--   carvia_coleta_recebimentos (1:1 com carvia_coletas) + carvia_coleta_recebimento_chassis
--   (1 linha por chassi/moto conferida). Ver app/carvia/models/coleta_recebimento.py.
--   Recebimento e por MOTO; backfill via reconciliacao (carvia_nf_veiculo_id preenchido depois).
-- Idempotente (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS carvia_coleta_recebimentos (
    id            SERIAL PRIMARY KEY,
    coleta_id     INTEGER NOT NULL UNIQUE REFERENCES carvia_coletas(id) ON DELETE CASCADE,
    status        VARCHAR(20) NOT NULL DEFAULT 'EM_RECEBIMENTO',
    iniciado_por  VARCHAR(150),
    iniciado_em   TIMESTAMP WITHOUT TIME ZONE,
    concluido_por VARCHAR(150),
    concluido_em  TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_carvia_receb_status ON carvia_coleta_recebimentos (status);

CREATE TABLE IF NOT EXISTS carvia_coleta_recebimento_chassis (
    id                   SERIAL PRIMARY KEY,
    recebimento_id       INTEGER NOT NULL REFERENCES carvia_coleta_recebimentos(id) ON DELETE CASCADE,
    chassi               VARCHAR(30) NOT NULL,
    modelo               VARCHAR(100),
    qr_code_lido         BOOLEAN NOT NULL DEFAULT FALSE,
    foto_s3_key          VARCHAR(500),
    carvia_nf_veiculo_id INTEGER REFERENCES carvia_nf_veiculos(id),
    status               VARCHAR(20) NOT NULL DEFAULT 'ALERTA',
    conferido_por        VARCHAR(150),
    conferido_em         TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_carvia_receb_chassi UNIQUE (recebimento_id, chassi)
);
CREATE INDEX IF NOT EXISTS idx_carvia_receb_chassi_receb ON carvia_coleta_recebimento_chassis (recebimento_id);
CREATE INDEX IF NOT EXISTS idx_carvia_receb_chassi_veic  ON carvia_coleta_recebimento_chassis (carvia_nf_veiculo_id);
CREATE INDEX IF NOT EXISTS idx_carvia_receb_chassi_status ON carvia_coleta_recebimento_chassis (status);
