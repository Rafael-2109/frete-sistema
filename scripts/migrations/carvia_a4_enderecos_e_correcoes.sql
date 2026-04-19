-- Migration A4.1 (2026-04-18) — Bug #4 do plano CarVia
-- 1. 8 colunas em carvia_operacoes (enderecos textuais remetente/destinatario)
-- 2. Nova tabela carvia_endereco_correcoes (audit trail de CC-e / correcao manual)
-- Idempotente (IF NOT EXISTS em tudo).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_a4_enderecos_e_correcoes.sql

BEGIN;

-- ── 1. Colunas em carvia_operacoes ──────────────────────────────────────
ALTER TABLE carvia_operacoes
    ADD COLUMN IF NOT EXISTS remetente_logradouro    VARCHAR(150),
    ADD COLUMN IF NOT EXISTS remetente_numero        VARCHAR(20),
    ADD COLUMN IF NOT EXISTS remetente_bairro        VARCHAR(150),
    ADD COLUMN IF NOT EXISTS remetente_cep           VARCHAR(10),
    ADD COLUMN IF NOT EXISTS destinatario_logradouro VARCHAR(150),
    ADD COLUMN IF NOT EXISTS destinatario_numero     VARCHAR(20),
    ADD COLUMN IF NOT EXISTS destinatario_bairro     VARCHAR(150),
    ADD COLUMN IF NOT EXISTS destinatario_cep        VARCHAR(10);

-- ── 2. Tabela carvia_endereco_correcoes ─────────────────────────────────
CREATE TABLE IF NOT EXISTS carvia_endereco_correcoes (
    id              SERIAL PRIMARY KEY,
    operacao_id     INTEGER NOT NULL
                    REFERENCES carvia_operacoes(id) ON DELETE CASCADE,
    campo           VARCHAR(40) NOT NULL,
    valor_anterior  VARCHAR(150),
    valor_novo      VARCHAR(150),
    motivo          VARCHAR(20) NOT NULL DEFAULT 'CORRECAO_MANUAL',
    numero_cce      VARCHAR(30),
    criado_em       TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    criado_por      VARCHAR(100)
);

-- Indices (obrigatorios por A4.2 — historico ordenado desc)
CREATE INDEX IF NOT EXISTS ix_carvia_endereco_correcoes_operacao_id
    ON carvia_endereco_correcoes (operacao_id);
CREATE INDEX IF NOT EXISTS ix_carvia_endereco_correcoes_operacao_criado
    ON carvia_endereco_correcoes (operacao_id, criado_em);
CREATE INDEX IF NOT EXISTS ix_carvia_endereco_correcoes_motivo_criado
    ON carvia_endereco_correcoes (motivo, criado_em);

COMMIT;
