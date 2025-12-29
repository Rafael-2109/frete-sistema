-- Script SQL para adicionar campos de snapshot de parametros de margem
-- Executar no Shell do Render

-- Adicionar campos de snapshot de parametros
ALTER TABLE carteira_principal
ADD COLUMN IF NOT EXISTS frete_percentual_snapshot NUMERIC(5, 2),
ADD COLUMN IF NOT EXISTS custo_financeiro_pct_snapshot NUMERIC(5, 2),
ADD COLUMN IF NOT EXISTS custo_operacao_pct_snapshot NUMERIC(5, 2),
ADD COLUMN IF NOT EXISTS percentual_perda_snapshot NUMERIC(5, 2);

-- Verificar campos adicionados
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'carteira_principal'
AND column_name IN (
    'frete_percentual_snapshot',
    'custo_financeiro_pct_snapshot',
    'custo_operacao_pct_snapshot',
    'percentual_perda_snapshot'
)
ORDER BY column_name;
