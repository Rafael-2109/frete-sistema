-- Migration HORA 24: tabela hora_tagplus_backfill_job
-- Background tracking de jobs de backfill TagPlus (queue hora_backfill).
-- Idempotente — usa IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS hora_tagplus_backfill_job (
    id                  SERIAL PRIMARY KEY,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    since               DATE,
    "until"             DATE,
    limite              INTEGER,
    operador            VARCHAR(100),
    rq_job_id           VARCHAR(80),
    iniciado_em         TIMESTAMP,
    finalizado_em       TIMESTAMP,
    total_listadas      INTEGER NOT NULL DEFAULT 0,
    processadas         INTEGER NOT NULL DEFAULT 0,
    n_criado            INTEGER NOT NULL DEFAULT 0,
    n_atualizado        INTEGER NOT NULL DEFAULT 0,
    n_inalterado        INTEGER NOT NULL DEFAULT 0,
    n_cancelado         INTEGER NOT NULL DEFAULT 0,
    n_pulada_cancelada  INTEGER NOT NULL DEFAULT 0,
    n_pulada_invalida   INTEGER NOT NULL DEFAULT 0,
    n_dup               INTEGER NOT NULL DEFAULT 0,
    n_erro              INTEGER NOT NULL DEFAULT 0,
    n_divergencias      INTEGER NOT NULL DEFAULT 0,
    ultimo_erro         TEXT,
    relatorio           JSON,
    criado_em           TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_backfill_job_status
    ON hora_tagplus_backfill_job (status);

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_backfill_job_criado_em
    ON hora_tagplus_backfill_job (criado_em DESC);

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_backfill_job_rq_job_id
    ON hora_tagplus_backfill_job (rq_job_id);
