-- Migration: Coletas CarVia ("papel de pao") — stream 3 do redesign
-- Data: 2026-06-17
-- Descricao:
--   Cria carvia_coletas (cabecalho: 1 veiculo, contratado, placa, valor, destino local_cd,
--   datas, despesa a conciliar) e carvia_coleta_nfs (linhas: NF rascunho + vinculo opcional
--   a CarviaNf real). Ver app/carvia/models/coleta.py.
-- Idempotente (CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS carvia_coletas (
    id                SERIAL PRIMARY KEY,
    contratado_nome   VARCHAR(255),
    transportadora_id INTEGER REFERENCES transportadoras(id),
    placa             VARCHAR(10),
    valor_coleta      NUMERIC(15, 2),
    local_cd          VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE',
    data_prevista     DATE,
    data_coletada     BOOLEAN NOT NULL DEFAULT FALSE,
    data_coletada_em  TIMESTAMP WITHOUT TIME ZONE,
    despesa_id        INTEGER REFERENCES carvia_despesas(id),
    status            VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
    observacoes       TEXT,
    criado_por        VARCHAR(150),
    criado_em         TIMESTAMP WITHOUT TIME ZONE,
    atualizado_em     TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_carvia_coletas_transportadora ON carvia_coletas (transportadora_id);
CREATE INDEX IF NOT EXISTS idx_carvia_coletas_despesa       ON carvia_coletas (despesa_id);
CREATE INDEX IF NOT EXISTS idx_carvia_coletas_status        ON carvia_coletas (status);

CREATE TABLE IF NOT EXISTS carvia_coleta_nfs (
    id                       SERIAL PRIMARY KEY,
    coleta_id                INTEGER NOT NULL REFERENCES carvia_coletas(id) ON DELETE CASCADE,
    numero_nf                VARCHAR(20),
    nome_cliente_rascunho    VARCHAR(255),
    cidade_destino           VARCHAR(120),
    qtd_motos                INTEGER,
    valor_frete              NUMERIC(15, 2),
    vendedor                 VARCHAR(150),
    transportadora_embarque  VARCHAR(255),
    carvia_nf_id             INTEGER REFERENCES carvia_nfs(id),
    criado_em                TIMESTAMP WITHOUT TIME ZONE,
    atualizado_em            TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_carvia_coleta_nfs_coleta    ON carvia_coleta_nfs (coleta_id);
CREATE INDEX IF NOT EXISTS idx_carvia_coleta_nfs_carvia_nf ON carvia_coleta_nfs (carvia_nf_id);
