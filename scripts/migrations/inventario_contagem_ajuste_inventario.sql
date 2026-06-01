-- Migration: adiciona coluna ajuste_inventario em inventario_contagem_item.
-- Idempotente (Render Shell). O backfill (ajuste_inventario = ajuste) só roda
-- quando a coluna é recém-criada, dentro do DO block — re-execução não toca dados.
--
-- Semântica (não confundir):
--   ajuste            = contagem − qtd_esperada → delta a aplicar no Odoo (skills).
--   ajuste_inventario = valor literal da coluna AJUSTE → soma na coluna INV/MOV do Confronto.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'inventario_contagem_item'
          AND column_name = 'ajuste_inventario'
    ) THEN
        ALTER TABLE inventario_contagem_item
            ADD COLUMN ajuste_inventario NUMERIC(15,3) NOT NULL DEFAULT 0;
        UPDATE inventario_contagem_item
            SET ajuste_inventario = ajuste
            WHERE ajuste IS NOT NULL;
    END IF;
END $$;
