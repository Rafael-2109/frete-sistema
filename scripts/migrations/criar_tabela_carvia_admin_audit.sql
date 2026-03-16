-- Migration: carvia_admin_audit
-- Tabela de auditoria para acoes administrativas no modulo CarVia
-- Registra hard deletes, type changes, re-links e edicoes admin

CREATE TABLE IF NOT EXISTS carvia_admin_audit (
    id SERIAL PRIMARY KEY,
    acao VARCHAR(30) NOT NULL,
    entidade_tipo VARCHAR(50) NOT NULL,
    entidade_id INTEGER NOT NULL,
    dados_snapshot JSONB NOT NULL,
    dados_relacionados JSONB,
    motivo TEXT NOT NULL,
    executado_por VARCHAR(100) NOT NULL,
    executado_em TIMESTAMP NOT NULL,
    detalhes JSONB
);

-- Indices
CREATE INDEX IF NOT EXISTS ix_carvia_audit_acao ON carvia_admin_audit (acao);
CREATE INDEX IF NOT EXISTS ix_carvia_audit_entidade ON carvia_admin_audit (entidade_tipo, entidade_id);
CREATE INDEX IF NOT EXISTS ix_carvia_audit_executado_em ON carvia_admin_audit (executado_em);
CREATE INDEX IF NOT EXISTS ix_carvia_audit_executado_por ON carvia_admin_audit (executado_por);

-- Check constraint (idempotente via DO block)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_carvia_audit_acao'
    ) THEN
        ALTER TABLE carvia_admin_audit
            ADD CONSTRAINT ck_carvia_audit_acao
            CHECK (acao IN ('HARD_DELETE', 'TYPE_CHANGE', 'RELINK', 'FIELD_EDIT', 'IMPORT_EDIT'));
    END IF;
END $$;
