-- Migration: Expandir precisao do percentual de comissao
-- NUMERIC(5,4) → NUMERIC(10,8) para suportar ate 8 casas decimais na fracao
-- Ex: 3.49116% = 0.0349116 (7 casas) — nao cabia em NUMERIC(5,4)

-- Tabela principal
ALTER TABLE carvia_comissao_fechamentos
  ALTER COLUMN percentual TYPE NUMERIC(10,8);

-- Tabela de snapshots (CTes)
ALTER TABLE carvia_comissao_fechamento_ctes
  ALTER COLUMN percentual_snapshot TYPE NUMERIC(10,8);

-- Atualizar CHECK constraint do percentual
ALTER TABLE carvia_comissao_fechamentos
  DROP CONSTRAINT IF EXISTS ck_comissao_percentual_range;

ALTER TABLE carvia_comissao_fechamentos
  ADD CONSTRAINT ck_comissao_percentual_range
  CHECK (percentual > 0 AND percentual <= 1);
