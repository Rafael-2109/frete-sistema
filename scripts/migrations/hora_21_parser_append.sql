-- Migration HORA #21 — Append-prompt versionado para o parser de DANFE.
-- Idempotente. Aplicar via Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/hora_21_parser_append.sql
--
-- Mecanismo: a cada erro de extracao reportado pelo operador, uma nova
-- versao do append e gravada (via UI). Apenas 1 ativa por vez.

CREATE TABLE IF NOT EXISTS hora_danfe_parser_append (
    id SERIAL PRIMARY KEY,
    versao INTEGER NOT NULL UNIQUE,
    texto_append TEXT NOT NULL,
    acrescimo_aplicado TEXT,
    motivo VARCHAR(500),
    criado_por VARCHAR(100),
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS ix_hora_danfe_parser_append_ativo
    ON hora_danfe_parser_append (ativo);

CREATE INDEX IF NOT EXISTS ix_hora_danfe_parser_append_criado_em
    ON hora_danfe_parser_append (criado_em);

-- Garantir que apenas 1 linha tenha ativo=TRUE
-- (cada nova versao precisa setar as antigas como ativo=FALSE no service).
CREATE UNIQUE INDEX IF NOT EXISTS uq_hora_danfe_parser_append_unico_ativo
    ON hora_danfe_parser_append (ativo) WHERE ativo = TRUE;
