-- Migration: tabelas do módulo inventario (idempotente)
-- Roda em Render Shell: \i scripts/migrations/inventario_create_tables.sql

CREATE TABLE IF NOT EXISTS inventario_ciclo (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(50) UNIQUE NOT NULL,
    data_snapshot DATE NOT NULL,
    descricao     VARCHAR(200),
    status        VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
    criado_em     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por    VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_inventario_ciclo_status ON inventario_ciclo(status);

CREATE TABLE IF NOT EXISTS inventario_base (
    id           SERIAL PRIMARY KEY,
    ciclo_id     INTEGER NOT NULL REFERENCES inventario_ciclo(id),
    cod_produto  VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(200),
    empresa      VARCHAR(10) NOT NULL,
    qtd          NUMERIC(15, 3) NOT NULL DEFAULT 0,
    CONSTRAINT uq_inv_base_ciclo_cod_empresa UNIQUE (ciclo_id, cod_produto, empresa)
);
CREATE INDEX IF NOT EXISTS ix_inventario_base_ciclo_id ON inventario_base(ciclo_id);
CREATE INDEX IF NOT EXISTS ix_inventario_base_cod_produto ON inventario_base(cod_produto);

CREATE TABLE IF NOT EXISTS inventario_ajuste_manual (
    id            SERIAL PRIMARY KEY,
    ciclo_id      INTEGER NOT NULL REFERENCES inventario_ciclo(id),
    cod_produto   VARCHAR(50) NOT NULL,
    nome_produto  VARCHAR(200),
    local         VARCHAR(20),
    qtd           NUMERIC(15, 3) NOT NULL,
    tipo_ajuste   VARCHAR(20),
    observacao    VARCHAR(500),
    criado_em     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por    VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_inventario_ajuste_manual_ciclo_id ON inventario_ajuste_manual(ciclo_id);
CREATE INDEX IF NOT EXISTS ix_inventario_ajuste_manual_cod_produto ON inventario_ajuste_manual(cod_produto);

CREATE TABLE IF NOT EXISTS inventario_snapshot_odoo (
    id             SERIAL PRIMARY KEY,
    ciclo_id       INTEGER NOT NULL REFERENCES inventario_ciclo(id),
    cod_produto    VARCHAR(50) NOT NULL,
    nome_produto   VARCHAR(200),
    estoque_fb     NUMERIC(15, 3) DEFAULT 0,
    estoque_cd     NUMERIC(15, 3) DEFAULT 0,
    estoque_lf     NUMERIC(15, 3) DEFAULT 0,
    pa_qtd         NUMERIC(15, 3) DEFAULT 0,
    componente_qtd NUMERIC(15, 3) DEFAULT 0,
    compras_qtd    NUMERIC(15, 3) DEFAULT 0,
    refresh_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inv_snapshot_ciclo_cod UNIQUE (ciclo_id, cod_produto)
);
CREATE INDEX IF NOT EXISTS ix_inventario_snapshot_odoo_ciclo_id ON inventario_snapshot_odoo(ciclo_id);
CREATE INDEX IF NOT EXISTS ix_inventario_snapshot_odoo_cod_produto ON inventario_snapshot_odoo(cod_produto);
