-- ============================================================
-- Script SQL: Adicionar campo atualizado_em em pedido_compras
-- ============================================================
-- Executar no Shell do Render ou diretamente no PostgreSQL
-- ============================================================

-- 1. Verificar se coluna já existe
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND column_name = 'atualizado_em';

-- 2. Adicionar coluna atualizado_em
ALTER TABLE pedido_compras
ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT NOW();

-- 3. Atualizar registros existentes (copiar de criado_em)
UPDATE pedido_compras
SET atualizado_em = criado_em
WHERE atualizado_em IS NULL;

-- 4. Verificar estrutura final
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'pedido_compras'
AND column_name IN ('criado_em', 'atualizado_em')
ORDER BY column_name;
