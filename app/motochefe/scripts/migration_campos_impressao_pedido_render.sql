-- ================================================================================
-- MIGRAÇÃO RENDER - Adiciona campos de impressão em pedido_venda_moto
-- Executar no Shell SQL do Render
-- ================================================================================

-- 1. Adicionar campo impresso (Boolean, default False)
ALTER TABLE pedido_venda_moto
ADD COLUMN IF NOT EXISTS impresso BOOLEAN DEFAULT FALSE NOT NULL;

-- 2. Adicionar campo impresso_por (String 100)
ALTER TABLE pedido_venda_moto
ADD COLUMN IF NOT EXISTS impresso_por VARCHAR(100);

-- 3. Adicionar campo impresso_em (DateTime)
ALTER TABLE pedido_venda_moto
ADD COLUMN IF NOT EXISTS impresso_em TIMESTAMP;

-- 4. Criar índice para busca rápida
CREATE INDEX IF NOT EXISTS idx_pedido_venda_impresso
ON pedido_venda_moto(impresso);

-- ================================================================================
-- VERIFICAÇÃO
-- ================================================================================

-- Ver estrutura dos campos criados
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pedido_venda_moto'
AND column_name IN ('impresso', 'impresso_por', 'impresso_em')
ORDER BY column_name;

-- Contar pedidos
SELECT COUNT(*) as total_pedidos FROM pedido_venda_moto;

-- Ver status de impressão
SELECT
    impresso,
    COUNT(*) as quantidade
FROM pedido_venda_moto
GROUP BY impresso;
