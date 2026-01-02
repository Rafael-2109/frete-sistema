-- Migration: Adiciona campos de conversao em NFDevolucaoLinha
-- Data: 01/01/2026
-- Uso: Executar no Shell do Render

-- Adicionar campo quantidade_convertida (quantidade convertida para caixas)
ALTER TABLE nf_devolucao_linha
ADD COLUMN IF NOT EXISTS quantidade_convertida NUMERIC(15, 3);

-- Adicionar campo qtd_por_caixa (unidades por caixa do nosso produto)
ALTER TABLE nf_devolucao_linha
ADD COLUMN IF NOT EXISTS qtd_por_caixa INTEGER;

-- Verificar
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'nf_devolucao_linha'
AND column_name IN ('quantidade_convertida', 'qtd_por_caixa');
