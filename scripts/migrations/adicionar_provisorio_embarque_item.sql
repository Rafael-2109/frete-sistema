-- Migration: Adicionar campos provisorio e carvia_cotacao_id em embarque_itens
-- Data: 2026-03-21
-- Descricao: Suporte a itens provisorios CarVia em embarques.
--   provisorio=TRUE: placeholder de cotacao aguardando pedidos/NF.
--   carvia_cotacao_id: rastreabilidade da cotacao CarVia de origem.
-- Uso: Executar no Render Shell (SQL idempotente)

-- Campo provisorio (boolean, default false)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embarque_itens' AND column_name = 'provisorio'
    ) THEN
        ALTER TABLE embarque_itens
            ADD COLUMN provisorio BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- Campo carvia_cotacao_id (integer nullable, referencia carvia_cotacoes)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embarque_itens' AND column_name = 'carvia_cotacao_id'
    ) THEN
        ALTER TABLE embarque_itens
            ADD COLUMN carvia_cotacao_id INTEGER NULL;
    END IF;
END $$;

-- Indice para busca rapida de provisorios por embarque
CREATE INDEX IF NOT EXISTS ix_embarque_itens_provisorio
    ON embarque_itens (embarque_id)
    WHERE provisorio = TRUE;

-- Indice para busca por cotacao CarVia
CREATE INDEX IF NOT EXISTS ix_embarque_itens_carvia_cotacao
    ON embarque_itens (carvia_cotacao_id)
    WHERE carvia_cotacao_id IS NOT NULL;
