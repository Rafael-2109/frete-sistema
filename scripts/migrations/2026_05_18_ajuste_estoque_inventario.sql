-- Migration: ajuste_estoque_inventario (enxuta, suporta multiplos ciclos)
-- Cada linha = uma divergencia (produto, company, lote) detectada em um ciclo.
-- Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §7.2

BEGIN;

CREATE TABLE IF NOT EXISTS ajuste_estoque_inventario (
    id SERIAL PRIMARY KEY,
    ciclo VARCHAR(40) NOT NULL,
    cod_produto VARCHAR(30) NOT NULL,
    tipo_produto SMALLINT NOT NULL,
    company_id INTEGER NOT NULL,
    lote_inventariado VARCHAR(60),
    lote_odoo VARCHAR(60),
    qtd_inventario NUMERIC(15,4) NOT NULL,
    qtd_odoo NUMERIC(15,4) NOT NULL,
    qtd_ajuste NUMERIC(15,4) NOT NULL,
    custo_medio NUMERIC(15,4),
    acao_decidida VARCHAR(30) NOT NULL,
    external_id_operacao VARCHAR(64),
    canary_passou BOOLEAN DEFAULT FALSE,
    aprovado_em TIMESTAMP,
    aprovado_por VARCHAR(80),
    status VARCHAR(20) NOT NULL DEFAULT 'PROPOSTO',
    erro_msg TEXT,
    criado_em TIMESTAMP NOT NULL,
    criado_por VARCHAR(80) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_aei_ciclo_chave
    ON ajuste_estoque_inventario (ciclo, company_id, cod_produto, lote_odoo);
CREATE INDEX IF NOT EXISTS idx_aei_status ON ajuste_estoque_inventario (status);
CREATE INDEX IF NOT EXISTS idx_aei_acao ON ajuste_estoque_inventario (acao_decidida);

COMMIT;
