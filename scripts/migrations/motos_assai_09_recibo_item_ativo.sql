-- Adiciona soft-delete em assai_recibo_item (coluna `ativo`) e troca o
-- UNIQUE (recibo_id, chassi) por UNIQUE PARCIAL para permitir re-importacao
-- de chassi previamente inativado.
--
-- Idempotente: pode rodar em ambientes que ja tenham coluna/indice.

-- 1) Coluna `ativo` (default TRUE para nao impactar dados existentes)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'assai_recibo_item' AND column_name = 'ativo'
    ) THEN
        ALTER TABLE assai_recibo_item
            ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
END $$;

-- 2) Drop do UNIQUE antigo (sem WHERE) — sera substituido por parcial
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'assai_recibo_item'
          AND indexname = 'ux_assai_recibo_item_recibo_chassi'
          AND indexdef NOT ILIKE '%WHERE%'
    ) THEN
        DROP INDEX ux_assai_recibo_item_recibo_chassi;
    END IF;
END $$;

-- 3) UNIQUE PARCIAL (apenas itens ativos)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'assai_recibo_item'
          AND indexname = 'ux_assai_recibo_item_recibo_chassi'
    ) THEN
        CREATE UNIQUE INDEX ux_assai_recibo_item_recibo_chassi
            ON assai_recibo_item(recibo_id, chassi)
            WHERE ativo = TRUE;
    END IF;
END $$;

-- 4) Indice auxiliar para detectar chassi duplicado em outros recibos ativos
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'assai_recibo_item'
          AND indexname = 'ix_assai_recibo_item_chassi_ativo'
    ) THEN
        CREATE INDEX ix_assai_recibo_item_chassi_ativo
            ON assai_recibo_item(chassi)
            WHERE ativo = TRUE;
    END IF;
END $$;
