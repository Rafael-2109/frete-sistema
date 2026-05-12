-- Motos Assaí — Migration 10: cabeçalho pedido x loja com 4 campos de agendamento
-- Idempotente; safe para re-execução.
--
-- Objetivo:
-- 1. Criar tabela `assai_pedido_venda_loja` (cabeçalho por (pedido, loja)).
-- 2. Backfill 1 linha por (pedido_id, loja_id) distinto em items existentes.
-- 3. Adicionar FK `pedido_loja_id` em `assai_pedido_venda_item`.
-- 4. Backfill FK nos items.
-- 5. Tornar `pedido_loja_id` NOT NULL.

CREATE TABLE IF NOT EXISTS assai_pedido_venda_loja (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id) ON DELETE CASCADE,
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    expedicao DATE,
    agendamento DATE,
    protocolo VARCHAR(50),
    agendamento_confirmado BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    atualizado_em TIMESTAMP,
    UNIQUE (pedido_id, loja_id)
);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_loja_pedido ON assai_pedido_venda_loja(pedido_id);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_loja_loja ON assai_pedido_venda_loja(loja_id);

-- Backfill: criar 1 cabeçalho por (pedido_id, loja_id) distinto.
-- INSERT EXPLICITO em TODOS os NOT NULL (agendamento_confirmado, criado_em)
-- para evitar dependencia do DEFAULT no DB — tabela pode ter sido criada via
-- db.create_all() sem DEFAULT (incidente 2026-05-12).
INSERT INTO assai_pedido_venda_loja
    (pedido_id, loja_id, agendamento_confirmado, criado_em)
SELECT DISTINCT
    pedido_id, loja_id, FALSE, (NOW() AT TIME ZONE 'America/Sao_Paulo')
FROM assai_pedido_venda_item
ON CONFLICT (pedido_id, loja_id) DO NOTHING;

-- Adicionar coluna pedido_loja_id em items (idempotente)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='assai_pedido_venda_item' AND column_name='pedido_loja_id'
    ) THEN
        ALTER TABLE assai_pedido_venda_item
            ADD COLUMN pedido_loja_id INTEGER
            REFERENCES assai_pedido_venda_loja(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Backfill FK em items
UPDATE assai_pedido_venda_item it
SET pedido_loja_id = pvl.id
FROM assai_pedido_venda_loja pvl
WHERE it.pedido_id = pvl.pedido_id
  AND it.loja_id = pvl.loja_id
  AND it.pedido_loja_id IS NULL;

-- Tornar NOT NULL apos backfill (idempotente)
DO $$
BEGIN
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
