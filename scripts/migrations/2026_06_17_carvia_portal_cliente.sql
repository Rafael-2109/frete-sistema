-- Migration: Portal do Cliente CarVia (usuario externo) — stream 5 do redesign
-- Data: 2026-06-17
-- Descricao:
--   carvia_portal_usuarios (usuario EXTERNO isolado do Usuario interno; login proprio) +
--   carvia_portal_usuario_cnpjs (CNPJs destino autorizados, modo CNPJ_DIRETO 8A).
--   Modo CLIENTE_COMERCIAL (8B) usa cliente_comercial_id -> CarviaCliente (CNPJs via
--   carvia_cliente_enderecos). Ver app/carvia/models/portal.py.
-- Idempotente (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS carvia_portal_usuarios (
    id                   SERIAL PRIMARY KEY,
    nome                 VARCHAR(255) NOT NULL,
    email                VARCHAR(255) NOT NULL UNIQUE,
    senha_hash           VARCHAR(255) NOT NULL,
    telefone             VARCHAR(20),
    status               VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    tipo_escopo          VARCHAR(20) NOT NULL DEFAULT 'CNPJ_DIRETO',
    cliente_comercial_id INTEGER REFERENCES carvia_clientes(id),
    criado_em            TIMESTAMP WITHOUT TIME ZONE,
    aprovado_por         VARCHAR(150),
    aprovado_em          TIMESTAMP WITHOUT TIME ZONE,
    ultimo_login_em      TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_carvia_portal_usuarios_status ON carvia_portal_usuarios (status);
CREATE INDEX IF NOT EXISTS idx_carvia_portal_usuarios_cc ON carvia_portal_usuarios (cliente_comercial_id);

CREATE TABLE IF NOT EXISTS carvia_portal_usuario_cnpjs (
    id                SERIAL PRIMARY KEY,
    portal_usuario_id INTEGER NOT NULL REFERENCES carvia_portal_usuarios(id) ON DELETE CASCADE,
    cnpj              VARCHAR(20) NOT NULL,
    nome_referencia   VARCHAR(255),
    CONSTRAINT uq_carvia_portal_usuario_cnpj UNIQUE (portal_usuario_id, cnpj)
);
CREATE INDEX IF NOT EXISTS idx_carvia_portal_uc_usuario ON carvia_portal_usuario_cnpjs (portal_usuario_id);
CREATE INDEX IF NOT EXISTS idx_carvia_portal_uc_cnpj ON carvia_portal_usuario_cnpjs (cnpj);
