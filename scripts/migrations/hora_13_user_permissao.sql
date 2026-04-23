-- Migration HORA 13: hora_user_permissao
-- Idempotente para Render Shell. Cria tabela + indice + constraint.

CREATE TABLE IF NOT EXISTS hora_user_permissao (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    modulo          VARCHAR(40) NOT NULL,
    pode_ver        BOOLEAN NOT NULL DEFAULT FALSE,
    pode_criar      BOOLEAN NOT NULL DEFAULT FALSE,
    pode_editar     BOOLEAN NOT NULL DEFAULT FALSE,
    pode_apagar     BOOLEAN NOT NULL DEFAULT FALSE,
    pode_aprovar    BOOLEAN NOT NULL DEFAULT FALSE,
    atualizado_em   TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    atualizado_por_id INTEGER NULL
);

-- Compat: tabela criada por uma versao anterior (sem pode_aprovar) recebe a coluna agora.
ALTER TABLE hora_user_permissao
    ADD COLUMN IF NOT EXISTS pode_aprovar BOOLEAN NOT NULL DEFAULT FALSE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_hora_user_perm_user_mod'
    ) THEN
        ALTER TABLE hora_user_permissao
        ADD CONSTRAINT uq_hora_user_perm_user_mod UNIQUE (user_id, modulo);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_hora_user_perm_lookup
    ON hora_user_permissao (user_id, modulo);

CREATE INDEX IF NOT EXISTS ix_hora_user_permissao_user_id
    ON hora_user_permissao (user_id);
