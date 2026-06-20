-- IMP-2026-06-19-007: manifesto S3 de uploads do chat do Agente Web.
-- 1 linha por arquivo enviado em /api/upload (dual-write /tmp + S3),
-- permite recuperar anexos de sessoes anteriores apos rotacao de sessao.
-- Idempotente (IF NOT EXISTS) — seguro para Render Shell.
CREATE TABLE IF NOT EXISTS agente_upload (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    session_id    VARCHAR(64) NOT NULL,
    file_id       VARCHAR(16) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    safe_name     VARCHAR(280) NOT NULL,
    s3_key        VARCHAR(512) NOT NULL,
    file_type     VARCHAR(20),
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    criado_em     TIMESTAMP NOT NULL,
    expira_em     TIMESTAMP,
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_agente_upload_user_safe UNIQUE (user_id, safe_name)
);
CREATE INDEX IF NOT EXISTS ix_agente_upload_user_id ON agente_upload (user_id);
CREATE INDEX IF NOT EXISTS ix_agente_upload_session_id ON agente_upload (session_id);
CREATE INDEX IF NOT EXISTS ix_agente_upload_expira_em ON agente_upload (expira_em);
CREATE INDEX IF NOT EXISTS ix_agente_upload_ativo ON agente_upload (ativo);
