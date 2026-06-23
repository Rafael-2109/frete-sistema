-- CarVia — Carta de Correcao (CCe) anexavel por NF/cotacao (N:N polimorfico)
-- Data: 2026-06-23. Idempotente. Safe para re-execucao.
-- Spec: docs/superpowers/specs/2026-06-23-carvia-propagacao-endereco-cce-design.md
--
-- (1) Tabela carvia_cartas_correcao (arquivo S3 da CCe + descricao)
-- (2) Tabela carvia_carta_correcao_vinculos (N:N polimorfico CCe <-> cotacao/nf)
--
-- Nota: db.create_all() no boot tambem cria (1) e (2) quando as tabelas estao
-- ausentes; este DDL e a fonte canonica/rastreavel (deploy Render).

-- (1) Cartas de Correcao (arquivo)
CREATE TABLE IF NOT EXISTS carvia_cartas_correcao (
    id              SERIAL PRIMARY KEY,
    nome_original   VARCHAR(255) NOT NULL,
    nome_arquivo    VARCHAR(255) NOT NULL,
    caminho_s3      VARCHAR(500) NOT NULL,
    tamanho_bytes   INTEGER,
    content_type    VARCHAR(100),
    descricao       TEXT,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    criado_por      VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_carvia_cartas_correcao_ativo
    ON carvia_cartas_correcao (ativo);

-- (2) Vinculos N:N polimorficos (CCe <-> cotacao/nf)
CREATE TABLE IF NOT EXISTS carvia_carta_correcao_vinculos (
    id              SERIAL PRIMARY KEY,
    carta_id        INTEGER NOT NULL REFERENCES carvia_cartas_correcao(id) ON DELETE CASCADE,
    entidade_tipo   VARCHAR(30) NOT NULL,
    entidade_id     INTEGER NOT NULL,
    origem          VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
    criado_em       TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo'),
    criado_por      VARCHAR(100) NOT NULL,
    CONSTRAINT uq_carvia_cce_vinculo UNIQUE (carta_id, entidade_tipo, entidade_id)
);
CREATE INDEX IF NOT EXISTS ix_carvia_carta_correcao_vinculos_carta_id
    ON carvia_carta_correcao_vinculos (carta_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cce_vinculo_entidade
    ON carvia_carta_correcao_vinculos (entidade_tipo, entidade_id);
