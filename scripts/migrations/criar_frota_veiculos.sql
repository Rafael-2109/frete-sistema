-- Migration: Criar modulo de controle de despesas da frota propria
-- Data: 2026-04-06
-- Idempotente: sim (IF NOT EXISTS em todos os objetos)

-- ============================================================
-- Tabela 1: Cadastro de veiculos da frota propria
-- ============================================================
CREATE TABLE IF NOT EXISTS frota_veiculos (
    id                  SERIAL PRIMARY KEY,
    placa               VARCHAR(10)     NOT NULL,
    marca               VARCHAR(50)     NOT NULL,
    modelo              VARCHAR(80)     NOT NULL,
    renavam             VARCHAR(15)     NOT NULL,
    proprietario        VARCHAR(120)    NOT NULL,
    ano_fabricacao      SMALLINT        NOT NULL,
    ano_modelo          SMALLINT        NOT NULL,
    cor                 VARCHAR(30),
    chassi              VARCHAR(25),
    veiculo_tipo_id     INTEGER         NOT NULL REFERENCES veiculos(id),
    transportadora_id   INTEGER         REFERENCES transportadoras(id),
    km_atual            INTEGER         NOT NULL DEFAULT 0,
    depreciacao_mensal  NUMERIC(15, 2)  DEFAULT 0,
    ativo               BOOLEAN         NOT NULL DEFAULT TRUE,
    observacoes         TEXT,
    criado_em           TIMESTAMP       NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100)    NOT NULL
);

-- Constraints UNIQUE
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_frota_veiculos_placa') THEN
        ALTER TABLE frota_veiculos ADD CONSTRAINT uq_frota_veiculos_placa UNIQUE (placa);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_frota_veiculos_renavam') THEN
        ALTER TABLE frota_veiculos ADD CONSTRAINT uq_frota_veiculos_renavam UNIQUE (renavam);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_frota_veiculos_chassi') THEN
        ALTER TABLE frota_veiculos ADD CONSTRAINT uq_frota_veiculos_chassi UNIQUE (chassi);
    END IF;
END $$;

-- Indices
CREATE INDEX IF NOT EXISTS ix_frota_veiculos_placa          ON frota_veiculos (placa);
CREATE INDEX IF NOT EXISTS ix_frota_veiculos_transportadora ON frota_veiculos (transportadora_id);
CREATE INDEX IF NOT EXISTS ix_frota_veiculos_ativo          ON frota_veiculos (ativo);

-- ============================================================
-- Tabela 2: Despesas dos veiculos da frota
-- ============================================================
CREATE TABLE IF NOT EXISTS frota_despesas (
    id                  SERIAL PRIMARY KEY,
    frota_veiculo_id    INTEGER         NOT NULL REFERENCES frota_veiculos(id),
    data_despesa        DATE            NOT NULL,
    km_no_momento       INTEGER         NOT NULL,
    categoria           VARCHAR(30)     NOT NULL,
    tipo_documento      VARCHAR(20)     NOT NULL DEFAULT 'SEM_DOCUMENTO',
    numero_documento    VARCHAR(60),
    valor               NUMERIC(15, 2)  NOT NULL,
    descricao           VARCHAR(255),
    observacoes         TEXT,
    -- Fase 2: integracao Odoo (colunas reservadas, nao usadas ainda)
    odoo_vendor_bill_id INTEGER,
    lancado_odoo_em     TIMESTAMP,
    lancado_odoo_por    VARCHAR(100),
    -- Audit
    criado_em           TIMESTAMP       NOT NULL DEFAULT NOW(),
    criado_por          VARCHAR(100)    NOT NULL
);

-- Indices
CREATE INDEX IF NOT EXISTS ix_frota_despesas_veiculo      ON frota_despesas (frota_veiculo_id);
CREATE INDEX IF NOT EXISTS ix_frota_despesas_data         ON frota_despesas (data_despesa DESC);
CREATE INDEX IF NOT EXISTS ix_frota_despesas_categoria    ON frota_despesas (categoria);
CREATE INDEX IF NOT EXISTS ix_frota_despesas_tipo_doc     ON frota_despesas (tipo_documento);
CREATE INDEX IF NOT EXISTS ix_frota_despesas_veiculo_data ON frota_despesas (frota_veiculo_id, data_despesa DESC);
