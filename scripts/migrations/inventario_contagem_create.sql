-- Migration: Inventário Cíclico (contagem parcial por quant)
-- Spec: docs/superpowers/specs/2026-05-31-inventario-ciclico-contagem-ajustes-design.md
-- Idempotente (IF NOT EXISTS) — seguro para Render Shell.

CREATE TABLE IF NOT EXISTS inventario_contagem (
    id                    SERIAL PRIMARY KEY,
    codigo                VARCHAR(50)  NOT NULL UNIQUE,
    empresa               VARCHAR(10)  NOT NULL,
    filtro_locais         JSON,
    filtro_codigos        JSON,
    incluir_indisponivel  BOOLEAN      NOT NULL DEFAULT FALSE,
    data_base             TIMESTAMP    NOT NULL,
    status                VARCHAR(20)  NOT NULL DEFAULT 'BASE_GERADA',
    descricao             VARCHAR(200),
    tot_itens             INTEGER      DEFAULT 0,
    tot_com_ajuste        INTEGER      DEFAULT 0,
    tot_ajuste_pos        NUMERIC(15,3) DEFAULT 0,
    tot_ajuste_neg        NUMERIC(15,3) DEFAULT 0,
    qt_lotes_novos        INTEGER      DEFAULT 0,
    criado_em             TIMESTAMP    NOT NULL,
    criado_por            VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS ix_inventario_contagem_empresa_data
    ON inventario_contagem (empresa, data_base);

CREATE TABLE IF NOT EXISTS inventario_contagem_item (
    id                  SERIAL PRIMARY KEY,
    contagem_id         INTEGER      NOT NULL REFERENCES inventario_contagem (id),
    location_name       VARCHAR(120) NOT NULL,
    location_id         INTEGER,
    local_tipo          VARCHAR(20),
    is_migracao         BOOLEAN      DEFAULT FALSE,
    cod_produto         VARCHAR(50)  NOT NULL,
    nome_produto        VARCHAR(200),
    lote                VARCHAR(60)  NOT NULL DEFAULT '',
    company_id          INTEGER,
    qtd_esperada        NUMERIC(15,3) DEFAULT 0,
    reservado_esperado  NUMERIC(15,3) DEFAULT 0,
    contagem            NUMERIC(15,3),
    ajuste              NUMERIC(15,3) DEFAULT 0,
    classe              VARCHAR(20),
    obs                 VARCHAR(300),
    CONSTRAINT uq_inv_contagem_item_quant
        UNIQUE (contagem_id, location_name, cod_produto, lote)
);

CREATE INDEX IF NOT EXISTS ix_inventario_contagem_item_contagem_id
    ON inventario_contagem_item (contagem_id);
CREATE INDEX IF NOT EXISTS ix_inventario_contagem_item_cod_produto
    ON inventario_contagem_item (cod_produto);
