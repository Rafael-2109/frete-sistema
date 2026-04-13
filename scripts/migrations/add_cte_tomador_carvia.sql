-- Adiciona campo cte_tomador em carvia_operacoes
-- Tomador do frete extraido do CTe XML (<ide>/<toma3> ou <toma4>)
-- Valores: REMETENTE | EXPEDIDOR | RECEBEDOR | DESTINATARIO | TERCEIRO

ALTER TABLE carvia_operacoes
  ADD COLUMN IF NOT EXISTS cte_tomador VARCHAR(20);
