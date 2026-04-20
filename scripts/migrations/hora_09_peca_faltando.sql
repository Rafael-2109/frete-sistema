-- Migration HORA 09: cria hora_peca_faltando + foto
-- Data: 2026-04-20
-- Descricao:
--   Pendencias N:1 de pecas ausentes em motos + galeria de fotos por pendencia.
--   `chassi_doador` preenchido quando a peca foi canibalizada de outra moto.
-- Idempotente: CREATE TABLE IF NOT EXISTS.
-- RISCO: baixo. Tabelas novas.

CREATE TABLE IF NOT EXISTS hora_peca_faltando (
    id SERIAL PRIMARY KEY,
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    descricao VARCHAR(255) NOT NULL,
    chassi_doador VARCHAR(30) NULL REFERENCES hora_moto(numero_chassi),
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
    recebimento_conferencia_id INTEGER NULL REFERENCES hora_recebimento_conferencia(id),
    observacoes TEXT NULL,
    criado_por VARCHAR(100) NULL,
    resolvido_por VARCHAR(100) NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    resolvido_em TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_peca_faltando_chassi
    ON hora_peca_faltando (numero_chassi);
CREATE INDEX IF NOT EXISTS ix_hora_peca_faltando_chassi_doador
    ON hora_peca_faltando (chassi_doador);
CREATE INDEX IF NOT EXISTS ix_hora_peca_faltando_status
    ON hora_peca_faltando (status);


CREATE TABLE IF NOT EXISTS hora_peca_faltando_foto (
    id SERIAL PRIMARY KEY,
    peca_faltando_id INTEGER NOT NULL REFERENCES hora_peca_faltando(id) ON DELETE CASCADE,
    foto_s3_key VARCHAR(500) NOT NULL,
    legenda VARCHAR(255) NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100) NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_peca_faltando_foto_peca
    ON hora_peca_faltando_foto (peca_faltando_id);
