-- Migration E9 (2026-04-19) — CarviaConferenciaHistorico (append-only log
-- de transicoes de status_conferencia em CarviaFrete). Resolve GAP-31.
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_e9_conferencia_historico.sql

BEGIN;

CREATE TABLE IF NOT EXISTS carvia_conferencia_historico (
    id                       SERIAL PRIMARY KEY,
    frete_id                 INTEGER NOT NULL
                             REFERENCES carvia_fretes(id) ON DELETE CASCADE,
    status_antes             VARCHAR(20),
    status_depois            VARCHAR(20) NOT NULL,
    valor_considerado_antes  NUMERIC(15, 2),
    valor_considerado_depois NUMERIC(15, 2),
    usuario                  VARCHAR(100) NOT NULL,
    data                     TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    detalhes_json            JSON
);

CREATE INDEX IF NOT EXISTS ix_carvia_conf_historico_frete_id
    ON carvia_conferencia_historico (frete_id);
CREATE INDEX IF NOT EXISTS ix_carvia_conf_historico_data
    ON carvia_conferencia_historico (data);
CREATE INDEX IF NOT EXISTS ix_carvia_conf_historico_frete_data
    ON carvia_conferencia_historico (frete_id, data);

COMMIT;
