-- Migration: Adicionar FK despesa_id em carvia_comissao_fechamentos
-- Vincula comissao a despesa para integracao com conciliacao bancaria

ALTER TABLE carvia_comissao_fechamentos
  ADD COLUMN IF NOT EXISTS despesa_id INTEGER REFERENCES carvia_despesas(id) ON DELETE SET NULL;

-- Unique parcial: cada despesa vincula no maximo 1 comissao
CREATE UNIQUE INDEX IF NOT EXISTS uq_comissao_fechamentos_despesa_id
  ON carvia_comissao_fechamentos (despesa_id) WHERE despesa_id IS NOT NULL;
