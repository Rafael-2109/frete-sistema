-- Migration: Adicionar ctrc_numero (CTRC SSW/SEFAZ) em carvia_operacoes e carvia_cte_complementares
-- Formato: CAR-{nCT}-{cDV} (ex: CAR-133-2)
-- Idempotente: IF NOT EXISTS

ALTER TABLE carvia_operacoes ADD COLUMN IF NOT EXISTS ctrc_numero VARCHAR(30);
ALTER TABLE carvia_cte_complementares ADD COLUMN IF NOT EXISTS ctrc_numero VARCHAR(30);

CREATE INDEX IF NOT EXISTS ix_carvia_operacoes_ctrc_numero ON carvia_operacoes(ctrc_numero);
CREATE INDEX IF NOT EXISTS ix_carvia_cte_complementares_ctrc_numero ON carvia_cte_complementares(ctrc_numero);
