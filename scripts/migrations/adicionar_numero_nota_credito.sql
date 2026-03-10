-- Migration: Adicionar numero_nota_credito a nf_devolucao
-- Permite exibir o numero da Nota de Credito nas reversoes.

ALTER TABLE nf_devolucao ADD COLUMN IF NOT EXISTS numero_nota_credito VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_nf_devolucao_numero_nota_credito
ON nf_devolucao(numero_nota_credito);
