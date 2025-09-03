-- =====================================================
-- ADICIONAR cotacao_id EM SEPARACAO
-- Data: 2025-01-29
-- =====================================================

-- 1. Adicionar campo cotacao_id em Separacao
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS cotacao_id INTEGER REFERENCES cotacoes(id);

-- 2. Criar índice para performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_cotacao_id 
ON separacao(cotacao_id)
WHERE cotacao_id IS NOT NULL;

-- 3. Migrar dados de Pedido para Separacao (se existirem)
UPDATE separacao s
SET cotacao_id = p.cotacao_id
FROM pedidos p
WHERE s.separacao_lote_id = p.separacao_lote_id
  AND s.num_pedido = p.num_pedido
  AND p.cotacao_id IS NOT NULL;

-- 4. Verificar resultado
SELECT 
    COUNT(*) as total_registros,
    COUNT(cotacao_id) as com_cotacao,
    COUNT(DISTINCT cotacao_id) as cotacoes_distintas
FROM separacao;