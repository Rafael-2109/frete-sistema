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
-- E DEFAULT NOW() em criado_em (mesma armadilha — Python default nao vira SQL DEFAULT)
ALTER TABLE assai_pedido_venda_loja
    ALTER COLUMN agendamento_confirmado SET DEFAULT FALSE;

ALTER TABLE assai_pedido_venda_loja
    ALTER COLUMN criado_em SET DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo');

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

-- ===== 2. Re-executar backfill da Migration 10 (INSERT explicito com TODOS os NOT NULL) =====
-- Idempotente via ON CONFLICT. Garante que cabecalhos existam para TODOS os
-- (pedido_id, loja_id) distintos em assai_pedido_venda_item.
-- TODOS os campos NOT NULL (agendamento_confirmado, criado_em) explicitos para
-- evitar dependencia de DEFAULT no DB (que pode estar ausente se create_all
-- criou a tabela).
INSERT INTO assai_pedido_venda_loja
    (pedido_id, loja_id, agendamento_confirmado, criado_em)
SELECT DISTINCT
    pedido_id, loja_id, FALSE, (NOW() AT TIME ZONE 'America/Sao_Paulo')
FROM assai_pedido_venda_item
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

-- Tornar NOT NULL (idempotente) — APENAS SE NAO HOUVER NULLs
-- ISSUE 1 (code review): RAISE EXCEPTION abortava transacao inteira, rollback
-- ate do DEFAULT fix. Trocar por skip silencioso; Python AFTER check captura.
DO $$
BEGIN
    -- So aplica SET NOT NULL se: (a) coluna ainda nullable; (b) zero rows com NULL
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_pedido_venda_item'
          AND column_name='pedido_loja_id'
          AND is_nullable='YES'
    ) AND NOT EXISTS (
        SELECT 1 FROM assai_pedido_venda_item WHERE pedido_loja_id IS NULL
    ) THEN
        ALTER TABLE assai_pedido_venda_item
            ALTER COLUMN pedido_loja_id SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_item_pedido_loja
    ON assai_pedido_venda_item(pedido_loja_id);

-- ===== 4. Defensive — outras tabelas com Boolean NOT NULL criadas via create_all =====
-- assai_separacao.agendamento_confirmado (Migration 11) tem mesma vulnerabilidade.
-- ISSUE 2 (code review): se Migration 11 nao rodou, coluna nao existe -> ALTER
-- falha -> rollback de TUDO. Guard com IF EXISTS antes.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_separacao'
          AND column_name='agendamento_confirmado'
    ) THEN
        -- Coluna existe — aplicar fix do DEFAULT
        ALTER TABLE assai_separacao
            ALTER COLUMN agendamento_confirmado SET DEFAULT FALSE;

        UPDATE assai_separacao
            SET agendamento_confirmado = FALSE
            WHERE agendamento_confirmado IS NULL;

        -- SET NOT NULL apenas se ainda nullable
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='assai_separacao'
              AND column_name='agendamento_confirmado'
              AND is_nullable='YES'
        ) THEN
            ALTER TABLE assai_separacao
                ALTER COLUMN agendamento_confirmado SET NOT NULL;
        END IF;
    END IF;
    -- Coluna nao existe (Migration 11 nao rodou): skip silencioso.
    -- Quando Migration 11 rodar no proximo deploy, coluna sera criada com
    -- server_default='false' do model -> DEFAULT correto desde o INSERT.
END $$;
