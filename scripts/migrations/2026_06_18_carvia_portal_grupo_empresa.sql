-- Migration: grupo_empresa no usuario do Portal do Cliente CarVia
-- Data: 2026-06-18
-- Descricao:
--   carvia_portal_usuarios.grupo_empresa (TEXT) — grupo/empresa que o cliente declara no
--   auto-cadastro; hint para o admin vincular ao CarviaCliente/grupo correto (nomes).
-- Idempotente (ADD COLUMN IF NOT EXISTS).

ALTER TABLE carvia_portal_usuarios
    ADD COLUMN IF NOT EXISTS grupo_empresa VARCHAR(255);
