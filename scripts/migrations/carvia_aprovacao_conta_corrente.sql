-- Migration: aprovacao de subcontratos + conta corrente transportadoras CarVia
--
-- Porta para o CarVia (esfera de Compra) os fluxos de "Em Tratativa" e
-- "Conta Corrente Considerado x Pago" do modulo Nacom (app/fretes/).
--
-- Ref:
--   .claude/plans/wobbly-tumbling-treasure.md
--   /tmp/subagent-findings/aprovacao_fretes_nacom.md
--   /tmp/subagent-findings/conta_corrente_nacom.md
--
-- Idempotente (IF NOT EXISTS). Seguro para rodar multiplas vezes.

BEGIN;

-- =====================================================================
-- 1. ALTER carvia_subcontratos — campos de pagamento + flag de tratativa
-- =====================================================================
ALTER TABLE carvia_subcontratos
    ADD COLUMN IF NOT EXISTS valor_pago        NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS valor_pago_em     TIMESTAMP,
    ADD COLUMN IF NOT EXISTS valor_pago_por    VARCHAR(100),
    ADD COLUMN IF NOT EXISTS requer_aprovacao  BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_carvia_sub_requer_aprovacao
    ON carvia_subcontratos (requer_aprovacao)
    WHERE requer_aprovacao = TRUE;


-- =====================================================================
-- 2. CREATE TABLE carvia_aprovacoes_subcontrato
-- =====================================================================
CREATE TABLE IF NOT EXISTS carvia_aprovacoes_subcontrato (
    id                       SERIAL PRIMARY KEY,
    subcontrato_id           INTEGER NOT NULL REFERENCES carvia_subcontratos(id),
    -- PENDENTE | APROVADO | REJEITADO
    status                   VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    solicitado_por           VARCHAR(100) NOT NULL,
    solicitado_em            TIMESTAMP NOT NULL DEFAULT NOW(),
    motivo_solicitacao       TEXT,
    -- Snapshot dos valores no momento da solicitacao
    valor_cotado_snap        NUMERIC(15, 2),
    valor_considerado_snap   NUMERIC(15, 2),
    valor_pago_snap          NUMERIC(15, 2),
    diferenca_snap           NUMERIC(15, 2),
    -- Decisao do aprovador
    aprovador                VARCHAR(100),
    aprovado_em              TIMESTAMP,
    observacoes_aprovacao    TEXT,
    lancar_diferenca         BOOLEAN DEFAULT FALSE,
    -- Auditoria
    criado_em                TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_carvia_aprov_status
        CHECK (status IN ('PENDENTE', 'APROVADO', 'REJEITADO'))
);

CREATE INDEX IF NOT EXISTS ix_carvia_aprov_sub_subcontrato_id
    ON carvia_aprovacoes_subcontrato (subcontrato_id);
CREATE INDEX IF NOT EXISTS ix_carvia_aprov_sub_status
    ON carvia_aprovacoes_subcontrato (status);
CREATE INDEX IF NOT EXISTS ix_carvia_aprov_sub_solicitado_em
    ON carvia_aprovacoes_subcontrato (solicitado_em);


-- =====================================================================
-- 3. CREATE TABLE carvia_conta_corrente_transportadoras
-- =====================================================================
CREATE TABLE IF NOT EXISTS carvia_conta_corrente_transportadoras (
    id                          SERIAL PRIMARY KEY,
    transportadora_id           INTEGER NOT NULL REFERENCES transportadoras(id),
    subcontrato_id              INTEGER NOT NULL REFERENCES carvia_subcontratos(id),
    fatura_transportadora_id    INTEGER REFERENCES carvia_faturas_transportadora(id),
    -- DEBITO  (CarVia pagou MENOS — devemos a transp.)
    -- CREDITO (CarVia pagou MAIS  — transp. nos deve)
    -- COMPENSACAO
    tipo_movimentacao           VARCHAR(20) NOT NULL,
    valor_diferenca             NUMERIC(15, 2) NOT NULL,
    valor_debito                NUMERIC(15, 2) NOT NULL DEFAULT 0,
    valor_credito               NUMERIC(15, 2) NOT NULL DEFAULT 0,
    descricao                   VARCHAR(255) NOT NULL,
    observacoes                 TEXT,
    -- ATIVO | COMPENSADO | DESCONSIDERADO
    status                      VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
    compensado_em               TIMESTAMP,
    compensado_por              VARCHAR(100),
    compensacao_subcontrato_id  INTEGER REFERENCES carvia_subcontratos(id),
    -- Auditoria
    criado_em                   TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por                  VARCHAR(100) NOT NULL,
    CONSTRAINT ck_carvia_cc_tipo
        CHECK (tipo_movimentacao IN ('DEBITO', 'CREDITO', 'COMPENSACAO')),
    CONSTRAINT ck_carvia_cc_dif
        CHECK (valor_diferenca >= 0),
    CONSTRAINT ck_carvia_cc_status
        CHECK (status IN ('ATIVO', 'COMPENSADO', 'DESCONSIDERADO'))
);

CREATE INDEX IF NOT EXISTS ix_carvia_cc_transp
    ON carvia_conta_corrente_transportadoras (transportadora_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cc_sub
    ON carvia_conta_corrente_transportadoras (subcontrato_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cc_fatura
    ON carvia_conta_corrente_transportadoras (fatura_transportadora_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cc_status
    ON carvia_conta_corrente_transportadoras (status);
CREATE INDEX IF NOT EXISTS ix_carvia_cc_criado_em
    ON carvia_conta_corrente_transportadoras (criado_em);

COMMIT;


-- Verificacao pos-migration (executar manualmente):
--
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'carvia_subcontratos'
--   AND column_name IN ('valor_pago', 'valor_pago_em', 'valor_pago_por', 'requer_aprovacao')
-- ORDER BY column_name;
--
-- SELECT COUNT(*) FROM carvia_aprovacoes_subcontrato;        -- esperado 0
-- SELECT COUNT(*) FROM carvia_conta_corrente_transportadoras; -- esperado 0
--
-- SELECT indexname FROM pg_indexes
-- WHERE tablename IN ('carvia_subcontratos',
--                     'carvia_aprovacoes_subcontrato',
--                     'carvia_conta_corrente_transportadoras')
--   AND indexname LIKE 'ix_carvia_%aprov%' OR indexname LIKE 'ix_carvia_cc%'
-- ORDER BY tablename, indexname;
