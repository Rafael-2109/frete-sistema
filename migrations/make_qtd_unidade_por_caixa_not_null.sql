-- ============================================================
-- Script SQL para RENDER: Tornar qtd_unidade_por_caixa NOT NULL
-- Campo necessário para conversão SKU→Unidade
-- Data: 2025-01-26
-- ============================================================

-- Passo 1: Verificar registros com NULL
SELECT COUNT(*) as registros_null
FROM recursos_producao
WHERE qtd_unidade_por_caixa IS NULL;

-- Passo 2: Se houver registros NULL, corrija primeiro (AJUSTAR O VALOR CONFORME NECESSÁRIO)
-- UPDATE recursos_producao
-- SET qtd_unidade_por_caixa = 1
-- WHERE qtd_unidade_por_caixa IS NULL;

-- Passo 3: Alterar tipo para INTEGER e tornar NOT NULL
ALTER TABLE recursos_producao
ALTER COLUMN qtd_unidade_por_caixa TYPE INTEGER,
ALTER COLUMN qtd_unidade_por_caixa SET NOT NULL;

-- Passo 4: Verificar resultado
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'recursos_producao'
AND column_name = 'qtd_unidade_por_caixa';

-- ✅ Migração concluída!
-- qtd_unidade_por_caixa agora é INTEGER NOT NULL
