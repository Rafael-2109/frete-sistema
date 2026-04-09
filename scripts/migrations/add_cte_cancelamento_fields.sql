-- =====================================================================
-- Migration: Cancelamento de CTe via XML do Outlook 365
-- Data: 2026-04-09
-- Objetivo: Adicionar suporte a marcacao de CTe cancelado e tabela
--           de pendencias de cancelamento
--
-- IDEMPOTENTE: Pode ser executado multiplas vezes sem erro.
-- EXECUTAR EM: Render Shell (psql $DATABASE_URL -f este_arquivo.sql)
-- =====================================================================

BEGIN;

-- =====================================================================
-- 1. Adicionar campos de cancelamento em conhecimento_transporte
-- =====================================================================

ALTER TABLE conhecimento_transporte
    ADD COLUMN IF NOT EXISTS cancelado BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE conhecimento_transporte
    ADD COLUMN IF NOT EXISTS data_cancelamento TIMESTAMP;

ALTER TABLE conhecimento_transporte
    ADD COLUMN IF NOT EXISTS protocolo_cancelamento VARCHAR(50);

ALTER TABLE conhecimento_transporte
    ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;

ALTER TABLE conhecimento_transporte
    ADD COLUMN IF NOT EXISTS cancelamento_origem VARCHAR(30);

-- Indice para buscas por status de cancelamento
CREATE INDEX IF NOT EXISTS ix_conhecimento_transporte_cancelado
    ON conhecimento_transporte (cancelado);

COMMENT ON COLUMN conhecimento_transporte.cancelado IS
    'True = CTe cancelado (via XML evento SEFAZ 110111 ou manual)';
COMMENT ON COLUMN conhecimento_transporte.data_cancelamento IS
    'Timestamp do evento de cancelamento (dhEvento do XML, se disponivel)';
COMMENT ON COLUMN conhecimento_transporte.protocolo_cancelamento IS
    'Numero do protocolo de cancelamento SEFAZ (nProt do retEvento)';
COMMENT ON COLUMN conhecimento_transporte.motivo_cancelamento IS
    'Justificativa do cancelamento (xJust do infEvento)';
COMMENT ON COLUMN conhecimento_transporte.cancelamento_origem IS
    'Origem da marcacao: OUTLOOK_XML, MANUAL, ODOO_SYNC';

-- =====================================================================
-- 2. Criar tabela cte_pendencia_cancelamento
-- =====================================================================

CREATE TABLE IF NOT EXISTS cte_pendencia_cancelamento (
    id SERIAL PRIMARY KEY,
    chave_acesso VARCHAR(44) NOT NULL,
    cte_id INTEGER REFERENCES conhecimento_transporte(id) ON DELETE SET NULL,
    frete_id INTEGER REFERENCES fretes(id) ON DELETE SET NULL,
    status VARCHAR(40) NOT NULL,
    mensagem TEXT,
    xml_raw TEXT,
    email_message_id VARCHAR(255),
    email_subject VARCHAR(500),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolvido_em TIMESTAMP,
    resolvido_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS ix_cte_pendencia_chave
    ON cte_pendencia_cancelamento (chave_acesso);
CREATE INDEX IF NOT EXISTS ix_cte_pendencia_status
    ON cte_pendencia_cancelamento (status);
CREATE INDEX IF NOT EXISTS ix_cte_pendencia_criado_em
    ON cte_pendencia_cancelamento (criado_em);
CREATE INDEX IF NOT EXISTS ix_cte_pendencia_cte_id
    ON cte_pendencia_cancelamento (cte_id);
CREATE INDEX IF NOT EXISTS ix_cte_pendencia_frete_id
    ON cte_pendencia_cancelamento (frete_id);

COMMENT ON TABLE cte_pendencia_cancelamento IS
    'Auditoria e pendencias do processamento automatico de cancelamento de CTe via Outlook XML';
COMMENT ON COLUMN cte_pendencia_cancelamento.status IS
    'CANCELADO_OK | PENDENTE_FATURA_CONFERIDA | ORPHAN | FRETE_CANCELADO_REVISAR | ERRO | CANCELAMENTO_ODOO_FALHOU';

COMMIT;

-- =====================================================================
-- Verificacao pos-migracao (executar manualmente)
-- =====================================================================
-- SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--  WHERE table_name = 'conhecimento_transporte'
--    AND column_name IN ('cancelado', 'data_cancelamento', 'protocolo_cancelamento',
--                        'motivo_cancelamento', 'cancelamento_origem');
--
-- SELECT column_name, data_type
--   FROM information_schema.columns
--  WHERE table_name = 'cte_pendencia_cancelamento'
--  ORDER BY ordinal_position;
