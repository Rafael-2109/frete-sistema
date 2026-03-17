-- Migration: Adicionar campo cte_pdf_path em carvia_operacoes e carvia_subcontratos
-- Armazena path do PDF original importado (DACTE PDF)
-- Executar no Render Shell

ALTER TABLE carvia_operacoes
ADD COLUMN IF NOT EXISTS cte_pdf_path VARCHAR(500);

ALTER TABLE carvia_subcontratos
ADD COLUMN IF NOT EXISTS cte_pdf_path VARCHAR(500);
