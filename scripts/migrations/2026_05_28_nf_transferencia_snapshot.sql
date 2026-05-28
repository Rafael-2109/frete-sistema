-- Migration 2026-05-28: cria tabelas de snapshot de NF inter-company (transferencia entre filiais)
-- Spec: nova tela /operacional/compras/relatorios/nf-transferencia
--
-- Idempotente: usa IF NOT EXISTS para Render Shell.

CREATE TABLE IF NOT EXISTS nf_transferencia_snapshot (
    id                       SERIAL PRIMARY KEY,
    -- Auditoria do refresh
    refresh_em               TIMESTAMP NOT NULL,
    refreshed_por            VARCHAR(100),
    -- NF origem (account.move out_invoice)
    chave_nfe                VARCHAR(50),
    numero_nf                VARCHAR(20),
    serie_nf                 VARCHAR(5),
    account_move_id_origem   INTEGER NOT NULL,
    account_move_name_origem VARCHAR(50),
    company_origem           VARCHAR(5) NOT NULL,
    company_destino          VARCHAR(5) NOT NULL,
    partner_origem_id        INTEGER,
    partner_destino_id       INTEGER,
    data_emissao             DATE,
    valor_total              NUMERIC(15, 2),
    acao                     VARCHAR(30),
    cfop_saida               VARCHAR(5),
    state_nf_origem          VARCHAR(20),
    -- DFe destino (l10n_br_ciel_it_account.dfe)
    dfe_id                   INTEGER,
    dfe_name                 VARCHAR(50),
    dfe_state                VARCHAR(30),
    dfe_situacao             VARCHAR(50),
    -- Picking destino (stock.picking)
    picking_id               INTEGER,
    picking_name             VARCHAR(50),
    picking_state            VARCHAR(30),
    -- Invoice destino (account.move in_invoice)
    invoice_destino_id       INTEGER,
    invoice_destino_name     VARCHAR(50),
    invoice_destino_state    VARCHAR(30),
    -- Status consolidado: PENDENTE_DFE / PENDENTE_PICKING / PENDENTE_INVOICE / CONCLUIDO / CANCELADA
    status_consolidado       VARCHAR(30) NOT NULL DEFAULT 'PENDENTE_DFE',
    observacao               TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nf_transf_snap_move_id
    ON nf_transferencia_snapshot (account_move_id_origem);

CREATE INDEX IF NOT EXISTS ix_nf_transf_snap_status
    ON nf_transferencia_snapshot (status_consolidado);

CREATE INDEX IF NOT EXISTS ix_nf_transf_snap_chave
    ON nf_transferencia_snapshot (chave_nfe);

CREATE INDEX IF NOT EXISTS ix_nf_transf_snap_emissao
    ON nf_transferencia_snapshot (data_emissao);

CREATE INDEX IF NOT EXISTS ix_nf_transf_snap_companies
    ON nf_transferencia_snapshot (company_origem, company_destino);


CREATE TABLE IF NOT EXISTS nf_transferencia_produto_snapshot (
    id              SERIAL PRIMARY KEY,
    nf_snapshot_id  INTEGER NOT NULL REFERENCES nf_transferencia_snapshot(id) ON DELETE CASCADE,
    cod_produto     VARCHAR(50) NOT NULL,
    nome_produto    VARCHAR(200),
    quantidade      NUMERIC(15, 3) NOT NULL DEFAULT 0,
    valor_unit      NUMERIC(15, 4),
    valor_total     NUMERIC(15, 2),
    cfop            VARCHAR(5),
    lote_nome       VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS ix_nf_transf_prod_nf
    ON nf_transferencia_produto_snapshot (nf_snapshot_id);

CREATE INDEX IF NOT EXISTS ix_nf_transf_prod_cod
    ON nf_transferencia_produto_snapshot (cod_produto);
