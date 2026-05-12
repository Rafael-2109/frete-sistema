-- Motos Assaí — Migration 15: HOTFIX para Migration 10 que falhou em produção
-- Data: 2026-05-12 11:00 UTC
-- Idempotente.
--
-- INCIDENTE: Migration 10 falhou em prod (Sentry PYTHON-FLASK-RT):
--   "null value in column agendamento_confirmado violates not-null constraint"
--
-- CAUSA RAIZ: db.create_all() no boot do Flask criou a tabela
-- `assai_pedido_venda_loja` ANTES da Migration 10 rodar. SQLAlchemy `default=False`
-- e Python-side, NAO vira DEFAULT FALSE no Postgres. Migration 10 (CREATE TABLE
-- IF NOT EXISTS) achou a tabela ja criada e nao re-aplicou DEFAULT. O INSERT do
-- backfill omitiu agendamento_confirmado -> NotNullViolation -> Migration 10
-- abortou -> pedido_loja_id nao foi adicionado em assai_pedido_venda_item ->
-- rotas motos_assai quebram com UndefinedColumn.
--
-- FIX:
-- 1. Garantir DEFAULT FALSE no DB (caso tabela criada via create_all)
-- 2. Defensive: UPDATE rows com NULL para FALSE
-- 3. Re-executar todo o backfill da Migration 10 explicitamente

-- ===== 1. Garantir DEFAULT FALSE em agendamento_confirmado =====
ALTER TABLE assai_pedido_venda_loja
    ALTER COLUMN agendamento_confirmado SET DEFAULT FALSE;

-- Garantir NOT NULL (idempotente — se ja era NOT NULL, no-op)
DO $$
BEGIN
    -- Defensive: se algum row foi inserido com NULL antes do fix, normaliza
    UPDATE assai_pedido_venda_loja
        SET agendamento_confirmado = FALSE
        WHERE agendamento_confirmado IS NULL;

    -- Reaplica NOT NULL caso tenha sido perdida na criacao via create_all
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_pedido_venda_loja'
          AND column_name='agendamento_confirmado'
          AND is_nullable='YES'
    ) THEN
        ALTER TABLE assai_pedido_venda_loja
            ALTER COLUMN agendamento_confirmado SET NOT NULL;
    END IF;
END $$;

-- ===== 2. Re-executar backfill da Migration 10 (INSERT explicito com FALSE) =====
-- Idempotente via ON CONFLICT. Garante que cabecalhos existam para TODOS os
-- (pedido_id, loja_id) distintos em assai_pedido_venda_item.
INSERT INTO assai_pedido_venda_loja (pedido_id, loja_id, agendamento_confirmado)
SELECT DISTINCT pedido_id, loja_id, FALSE FROM assai_pedido_venda_item
ON CONFLICT (pedido_id, loja_id) DO NOTHING;

-- ===== 3. Garantir coluna pedido_loja_id em items + backfill + NOT NULL =====
DO $$
BEGIN
    -- Adicionar coluna se nao existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_pedido_venda_item' AND column_name='pedido_loja_id'
    ) THEN
        ALTER TABLE assai_pedido_venda_item
            ADD COLUMN pedido_loja_id INTEGER
            REFERENCES assai_pedido_venda_loja(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Backfill FK em items (idempotente — apenas onde IS NULL)
UPDATE assai_pedido_venda_item it
SET pedido_loja_id = pvl.id
FROM assai_pedido_venda_loja pvl
WHERE it.pedido_id = pvl.pedido_id
  AND it.loja_id = pvl.loja_id
  AND it.pedido_loja_id IS NULL;

-- Tornar NOT NULL (idempotente)
DO $$
BEGIN
    -- Verificar que nao ha NULL antes de SET NOT NULL
    IF EXISTS (
        SELECT 1 FROM assai_pedido_venda_item WHERE pedido_loja_id IS NULL
    ) THEN
        RAISE EXCEPTION 'Existem items com pedido_loja_id NULL — backfill incompleto. Investigar.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_pedido_venda_item'
          AND column_name='pedido_loja_id'
          AND is_nullable='YES'
    ) THEN
        ALTER TABLE assai_pedido_venda_item
            ALTER COLUMN pedido_loja_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_item_pedido_loja
    ON assai_pedido_venda_item(pedido_loja_id);

-- ===== 4. Defensive — outras tabelas com Boolean NOT NULL criadas via create_all =====
-- assai_separacao.agendamento_confirmado (Migration 11) tem mesma vulnerabilidade
ALTER TABLE assai_separacao
    ALTER COLUMN agendamento_confirmado SET DEFAULT FALSE;

DO $$
BEGIN
    UPDATE assai_separacao
        SET agendamento_confirmado = FALSE
        WHERE agendamento_confirmado IS NULL;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_separacao'
          AND column_name='agendamento_confirmado'
          AND is_nullable='YES'
    ) THEN
        ALTER TABLE assai_separacao
            ALTER COLUMN agendamento_confirmado SET NOT NULL;
    END IF;
END $$;
