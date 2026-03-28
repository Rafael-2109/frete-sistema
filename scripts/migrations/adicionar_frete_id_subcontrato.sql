-- Migration: adicionar_frete_id_subcontrato
-- Descricao: Adiciona coluna frete_id em carvia_subcontratos para suportar
--            N subcontratos por frete (multi-leg transport).
--            Inverte a FK: ao inves de CarviaFrete.subcontrato_id (1:1),
--            usa CarviaSubcontrato.frete_id (N:1).
-- Data: 2026-03-28

-- DDL: adicionar coluna + indice
ALTER TABLE carvia_subcontratos
  ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id);

CREATE INDEX IF NOT EXISTS ix_carvia_subcontratos_frete_id
  ON carvia_subcontratos(frete_id);

-- Backfill: popular frete_id a partir de CarviaFrete.subcontrato_id existente
UPDATE carvia_subcontratos s
SET frete_id = f.id
FROM carvia_fretes f
WHERE f.subcontrato_id = s.id
  AND s.frete_id IS NULL;
