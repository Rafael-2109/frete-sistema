-- ============================================================
-- HORA 21: Cadastro de pecas (hora_peca + hora_tagplus_peca_map)
-- Idempotente: re-executar e seguro.
-- ============================================================

CREATE TABLE IF NOT EXISTS hora_peca (
    id                   SERIAL PRIMARY KEY,
    codigo_interno       VARCHAR(50) NOT NULL UNIQUE,
    descricao            VARCHAR(255) NOT NULL,
    ncm                  VARCHAR(10),
    cfop_default         VARCHAR(5) NOT NULL DEFAULT '5.102',
    unidade              VARCHAR(5) NOT NULL DEFAULT 'UN',
    preco_venda_padrao   NUMERIC(15, 2) NOT NULL DEFAULT 0,
    foto_s3_key          VARCHAR(500),
    ativo                BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em            TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_peca_ativo ON hora_peca(ativo);
CREATE INDEX IF NOT EXISTS ix_hora_peca_codigo_interno ON hora_peca(codigo_interno);

CREATE TABLE IF NOT EXISTS hora_tagplus_peca_map (
    id                   SERIAL PRIMARY KEY,
    peca_id              INTEGER NOT NULL UNIQUE REFERENCES hora_peca(id),
    tagplus_produto_id   VARCHAR(50) NOT NULL,
    tagplus_codigo       VARCHAR(50),
    cfop_default         VARCHAR(5),
    criado_em            TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_peca_map_codigo
    ON hora_tagplus_peca_map(tagplus_codigo);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_peca_map_produto_id
    ON hora_tagplus_peca_map(tagplus_produto_id);
