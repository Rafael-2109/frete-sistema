-- Migration: operacao_odoo_auditoria (polimorfica, reutilizavel)
-- Substitui o padrao fretes-especifico (LancamentoFreteOdooAuditoria) por uma
-- tabela polimorfica que pode auditar QUALQUER operacao Odoo (account.move,
-- stock.picking, stock.lot, stock.location).
-- Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §7.1

BEGIN;

CREATE TABLE IF NOT EXISTS operacao_odoo_auditoria (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(64) NOT NULL UNIQUE,
    tabela_origem VARCHAR(40) NOT NULL,
    registro_id INTEGER NOT NULL,
    acao VARCHAR(20) NOT NULL,
    modelo_odoo VARCHAR(60) NOT NULL,
    metodo_odoo VARCHAR(60),
    odoo_id INTEGER,
    etapa INTEGER,
    etapa_descricao VARCHAR(80),
    status VARCHAR(20) NOT NULL,
    payload_json JSONB,
    resposta_json JSONB,
    dados_antes_json JSONB,
    dados_depois_json JSONB,
    erro_msg TEXT,
    tempo_execucao_ms INTEGER,
    contexto_origem VARCHAR(40),
    contexto_ref VARCHAR(80),
    screenshot_s3_key VARCHAR(255),
    executado_em TIMESTAMP NOT NULL,
    executado_por VARCHAR(80) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oaa_tabela_odoo ON operacao_odoo_auditoria (tabela_origem, odoo_id);
CREATE INDEX IF NOT EXISTS idx_oaa_contexto ON operacao_odoo_auditoria (contexto_origem, contexto_ref);
CREATE INDEX IF NOT EXISTS idx_oaa_status ON operacao_odoo_auditoria (status);

COMMIT;
