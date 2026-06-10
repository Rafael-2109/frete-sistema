-- Migration: identidade unificada Teams <-> Web (plano 2026-06-10-teams-melhorias, Fase A)
-- 1. usuarios.teams_user_id        -> AAD object ID do Microsoft Teams (vinculo confirmado)
-- 2. usuarios.teams_vinculo_origem -> 'codigo' | 'email' | 'admin'
-- 3. teams_vinculo_codigos         -> codigos de pareamento (sha256, TTL, uso unico)
-- Idempotente: pode rodar 2x sem efeito (IF NOT EXISTS).

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS teams_user_id VARCHAR(64);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS teams_vinculo_origem VARCHAR(20);

CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_teams_user_id
    ON usuarios (teams_user_id) WHERE teams_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS teams_vinculo_codigos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES usuarios(id),
    codigo_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_teams_vinculo_codigos_hash
    ON teams_vinculo_codigos (codigo_hash);
