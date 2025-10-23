-- ============================================================================
-- SCRIPT 2: Adicionar FK fatura_frete_id em DespesaExtra (SQL para Render)
-- Objetivo: Adiciona a coluna sem quebrar o sistema existente
-- Executar: No Shell do Render
-- Data: 2025-01-23
-- ============================================================================

-- Verificar se a coluna já existe
SELECT column_name
FROM information_schema.columns
WHERE table_name='despesas_extras'
AND column_name='fatura_frete_id';

-- Se a query acima retornar vazio, executar os comandos abaixo:

-- 1. Adicionar coluna (nullable para não quebrar registros existentes)
ALTER TABLE despesas_extras
ADD COLUMN fatura_frete_id INTEGER;

-- 2. Adicionar Foreign Key constraint
ALTER TABLE despesas_extras
ADD CONSTRAINT fk_despesa_extra_fatura_frete
FOREIGN KEY (fatura_frete_id)
REFERENCES faturas_frete(id)
ON DELETE SET NULL;

-- 3. Adicionar índice para performance
CREATE INDEX idx_despesas_extras_fatura_frete_id
ON despesas_extras(fatura_frete_id);

-- 4. Verificar resultado
SELECT
    'Coluna criada' as status,
    COUNT(*) as total_despesas,
    SUM(CASE WHEN fatura_frete_id IS NULL THEN 1 ELSE 0 END) as despesas_sem_fk,
    SUM(CASE WHEN fatura_frete_id IS NOT NULL THEN 1 ELSE 0 END) as despesas_com_fk
FROM despesas_extras;
