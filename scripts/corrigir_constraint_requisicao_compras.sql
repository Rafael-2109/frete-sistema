-- =====================================================
-- Script para CORRIGIR constraint em requisicao_compras
-- Remove UNIQUE de num_requisicao e adiciona UNIQUE em (num_requisicao + cod_produto)
-- =====================================================
-- Comando: psql $DATABASE_URL < scripts/corrigir_constraint_requisicao_compras.sql
-- =====================================================

-- Mostrar constraint atual
SELECT
    conname as constraint_name,
    contype as constraint_type
FROM pg_constraint
WHERE conrelid = 'requisicao_compras'::regclass
AND contype = 'u';  -- unique constraints

-- =====================================================
-- PASSO 1: Remover índice UNIQUE de num_requisicao
-- =====================================================

DROP INDEX IF EXISTS ix_requisicao_compras_num_requisicao;

SELECT '✅ Índice UNIQUE removido de num_requisicao' as resultado;

-- =====================================================
-- PASSO 2: Recriar índice SEM unique (apenas index)
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_requisicao_num
ON requisicao_compras(num_requisicao);

SELECT '✅ Índice simples criado em num_requisicao' as resultado;

-- =====================================================
-- PASSO 3: Adicionar UNIQUE em odoo_id (ID da linha)
-- =====================================================

-- Remover constraint se existir
ALTER TABLE requisicao_compras
DROP CONSTRAINT IF EXISTS requisicao_compras_odoo_id_key;

-- Adicionar UNIQUE em odoo_id
ALTER TABLE requisicao_compras
ADD CONSTRAINT uq_requisicao_odoo_id UNIQUE (odoo_id);

SELECT '✅ UNIQUE adicionado em odoo_id' as resultado;

-- =====================================================
-- PASSO 4: Adicionar UNIQUE em (num_requisicao + cod_produto)
-- =====================================================

-- Remover se existir
ALTER TABLE requisicao_compras
DROP CONSTRAINT IF EXISTS uq_requisicao_produto;

-- Adicionar constraint composta
ALTER TABLE requisicao_compras
ADD CONSTRAINT uq_requisicao_produto
UNIQUE (num_requisicao, cod_produto);

SELECT '✅ UNIQUE composto adicionado (num_requisicao + cod_produto)' as resultado;

-- =====================================================
-- Verificar constraints finais
-- =====================================================

SELECT
    conname as constraint_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'requisicao_compras'::regclass
AND contype = 'u'
ORDER BY conname;

-- =====================================================
-- Mensagem final
-- =====================================================

SELECT '✅ Constraints corrigidas com sucesso!' as status;
SELECT 'ℹ️  Agora uma requisição pode ter MÚLTIPLAS LINHAS de produtos' as info;
SELECT 'ℹ️  UNIQUE está em: (num_requisicao + cod_produto) e (odoo_id)' as detalhe;
