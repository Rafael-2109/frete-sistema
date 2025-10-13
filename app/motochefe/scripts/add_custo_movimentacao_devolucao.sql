-- Script SQL para adicionar campo custo_movimentacao_devolucao em CustosOperacionais
-- Executar no Shell do Render

-- Verificar se coluna já existe
SELECT column_name
FROM information_schema.columns
WHERE table_name='custos_operacionais'
AND column_name='custo_movimentacao_devolucao';

-- Se não existir, adicionar
ALTER TABLE custos_operacionais
ADD COLUMN IF NOT EXISTS custo_movimentacao_devolucao NUMERIC(15, 2) NOT NULL DEFAULT 0;

-- Verificar criação
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name='custos_operacionais'
AND column_name='custo_movimentacao_devolucao';

-- ⚠️ IMPORTANTE: Configurar o valor no registro vigente
-- Exemplo (ajuste o valor conforme necessário):
-- UPDATE custos_operacionais
-- SET custo_movimentacao_devolucao = 50.00
-- WHERE ativo = TRUE AND data_vigencia_fim IS NULL;
