-- Migration: criar tabela carvia_previnculos_extrato_cotacao
-- Feature: Pre-vinculo de Linha de Extrato a Cotacao CarVia
-- Idempotente: pode ser rodada multiplas vezes no Render Shell sem erro.

CREATE TABLE IF NOT EXISTS carvia_previnculos_extrato_cotacao (
    id SERIAL PRIMARY KEY,
    extrato_linha_id INTEGER NOT NULL
        REFERENCES carvia_extrato_linhas(id) ON DELETE CASCADE,
    cotacao_id INTEGER NOT NULL
        REFERENCES carvia_cotacoes(id) ON DELETE CASCADE,
    valor_alocado NUMERIC(15, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
    conciliacao_id INTEGER
        REFERENCES carvia_conciliacoes(id) ON DELETE SET NULL,
    fatura_cliente_id INTEGER
        REFERENCES carvia_faturas_cliente(id) ON DELETE SET NULL,
    resolvido_em TIMESTAMP,
    resolvido_automatico BOOLEAN NOT NULL DEFAULT FALSE,
    cancelado_em TIMESTAMP,
    cancelado_por VARCHAR(100),
    motivo_cancelamento TEXT,
    observacao TEXT,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CHECK constraints idempotentes via DO block
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_previnculo_valor_positivo'
    ) THEN
        ALTER TABLE carvia_previnculos_extrato_cotacao
            ADD CONSTRAINT ck_previnculo_valor_positivo
            CHECK (valor_alocado > 0);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_previnculo_status'
    ) THEN
        ALTER TABLE carvia_previnculos_extrato_cotacao
            ADD CONSTRAINT ck_previnculo_status
            CHECK (status IN ('ATIVO', 'RESOLVIDO', 'CANCELADO'));
    END IF;
END $$;

-- Indices idempotentes (IF NOT EXISTS nativo)
CREATE INDEX IF NOT EXISTS ix_previnculo_extrato_linha_id
    ON carvia_previnculos_extrato_cotacao (extrato_linha_id);

CREATE INDEX IF NOT EXISTS ix_previnculo_cotacao_id
    ON carvia_previnculos_extrato_cotacao (cotacao_id);

CREATE INDEX IF NOT EXISTS ix_previnculo_status
    ON carvia_previnculos_extrato_cotacao (status);

CREATE INDEX IF NOT EXISTS ix_previnculo_ativo
    ON carvia_previnculos_extrato_cotacao (cotacao_id, status);

CREATE INDEX IF NOT EXISTS ix_previnculo_resolvido
    ON carvia_previnculos_extrato_cotacao (status, resolvido_em);

-- UNIQUE PARCIAL: apenas 1 pre-vinculo ATIVO por (linha, cotacao).
-- Permite recriar apos CANCELADO, e coexistir com RESOLVIDO historico.
CREATE UNIQUE INDEX IF NOT EXISTS uq_previnculo_linha_cotacao_ativo
    ON carvia_previnculos_extrato_cotacao (extrato_linha_id, cotacao_id)
    WHERE status = 'ATIVO';

-- Verificacao final
SELECT
    'Tabela criada' as status,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_name = 'carvia_previnculos_extrato_cotacao') as colunas,
    (SELECT COUNT(*) FROM pg_constraint
     WHERE conrelid = 'carvia_previnculos_extrato_cotacao'::regclass
     AND conname LIKE '%previnculo%') as check_constraints,
    (SELECT COUNT(*) FROM pg_indexes
     WHERE tablename = 'carvia_previnculos_extrato_cotacao') as indices;
