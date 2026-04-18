-- Migration HORA 03: acrescenta sistema_lojas + loja_hora_id em usuarios
-- Data: 2026-04-18
-- Descricao:
--   sistema_lojas BOOLEAN: flag de acesso ao modulo Lojas HORA.
--   loja_hora_id INTEGER NULL: segregacao por loja. NULL = acesso a todas; <id> = restrito.
--   Sem FK para hora_loja (evita acoplamento app/auth -> app/hora).
-- Idempotente: usa IF NOT EXISTS.
-- RISCO: baixo. Somente ADD COLUMN.

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS sistema_lojas BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS loja_hora_id INTEGER NULL;

CREATE INDEX IF NOT EXISTS ix_usuarios_loja_hora_id
    ON usuarios (loja_hora_id)
    WHERE loja_hora_id IS NOT NULL;
