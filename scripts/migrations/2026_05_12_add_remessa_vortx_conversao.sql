-- =============================================================================
-- Migration: remessa_vortx_conversao
-- Data: 2026-05-12
-- Descricao: Auditoria de Conversor (BMP/274 -> VORTX/310) e Validador read-only
--            de arquivos CNAB 400 externos.
-- Idempotente via IF NOT EXISTS / DO blocks.
-- =============================================================================

CREATE TABLE IF NOT EXISTS remessa_vortx_conversao (
  id                     SERIAL PRIMARY KEY,
  tipo                   VARCHAR(20) NOT NULL,
  nome_arquivo_original  VARCHAR(255) NOT NULL,
  arquivo_original       BYTEA NULL,
  arquivo_convertido     BYTEA NULL,
  banco_origem           VARCHAR(3) NULL,
  qtd_titulos            INTEGER NOT NULL DEFAULT 0,
  qtd_alteracoes         INTEGER NOT NULL DEFAULT 0,
  qtd_avisos             INTEGER NOT NULL DEFAULT 0,
  qtd_checks_falha       INTEGER NOT NULL DEFAULT 0,
  multa_codigo           VARCHAR(1) NULL,
  resultado              JSONB NULL,
  sucesso                BOOLEAN NOT NULL DEFAULT TRUE,
  erro                   TEXT NULL,
  criado_em              TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
  criado_por_id          INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
  CONSTRAINT remessa_vortx_conversao_tipo_check
    CHECK (tipo IN ('CONVERSAO', 'VALIDACAO'))
);

CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_tipo_idx
  ON remessa_vortx_conversao (tipo);

CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_banco_origem_idx
  ON remessa_vortx_conversao (banco_origem)
  WHERE banco_origem IS NOT NULL;

CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_sucesso_idx
  ON remessa_vortx_conversao (sucesso);

CREATE INDEX IF NOT EXISTS remessa_vortx_conversao_criado_em_idx
  ON remessa_vortx_conversao (criado_em DESC);

COMMENT ON TABLE remessa_vortx_conversao IS
  '2026-05-12: auditoria de operacoes de conversao (BMP/274 -> VORTX/310) e '
  'validacao de arquivos CNAB 400 externos. tipo IN (CONVERSAO, VALIDACAO). '
  'CONVERSAO grava arquivo_convertido para re-download; VALIDACAO grava apenas '
  'relatorio em resultado JSONB.';
