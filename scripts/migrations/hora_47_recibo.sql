-- Migration HORA 47: Recibo Simples (documento NAO-fiscal) de pecas/oficina.
-- Roadmap #1b. Idempotente (IF NOT EXISTS). Rodar no Render Shell.
--
-- Numeracao sequencial GLOBAL via sequence dedicada. PDF persistido no S3.
-- Coexiste com a NFe da venda (independentes).

CREATE SEQUENCE IF NOT EXISTS hora_recibo_numero_seq START 1;

CREATE TABLE IF NOT EXISTS hora_recibo (
    id              SERIAL PRIMARY KEY,
    numero          INTEGER NOT NULL UNIQUE,
    venda_id        INTEGER NOT NULL REFERENCES hora_venda (id),
    valor_total     NUMERIC(15, 2) NOT NULL DEFAULT 0,
    pdf_s3_key      VARCHAR(500),
    status          VARCHAR(20) NOT NULL DEFAULT 'EMITIDO',
    emitido_em      TIMESTAMP NOT NULL,
    emitido_por     VARCHAR(100),
    cancelado_em    TIMESTAMP,
    cancelado_por   VARCHAR(100),
    cancelamento_motivo VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_hora_recibo_venda_id ON hora_recibo (venda_id);
CREATE INDEX IF NOT EXISTS idx_hora_recibo_status ON hora_recibo (status);
