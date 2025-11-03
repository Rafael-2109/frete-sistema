-- =====================================================
-- Script DEFINITIVO para CORRIGIR constraint em requisicao_compras
-- Remove FK, corrige índice UNIQUE e recria FK
-- =====================================================
-- Comando: psql $DATABASE_URL < scripts/corrigir_constraint_final.sql
-- =====================================================

-- Mostrar estado atual
SELECT '========================================' as msg;
SELECT '🔍 ESTADO ATUAL' as msg;
SELECT '========================================' as msg;

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'requisicao_compras'
AND indexname LIKE '%num_requisicao%';

-- =====================================================
-- PASSO 1: Remover FK de pedido_compras
-- =====================================================

ALTER TABLE pedido_compras
DROP CONSTRAINT IF EXISTS pedido_compras_num_requisicao_fkey CASCADE;

SELECT '✅ FK removida de pedido_compras' as resultado;

-- =====================================================
-- PASSO 2: Remover índice UNIQUE problemático
-- =====================================================

DROP INDEX IF EXISTS ix_requisicao_compras_num_requisicao CASCADE;

SELECT '✅ Índice UNIQUE removido de num_requisicao' as resultado;

-- =====================================================
-- PASSO 3: Recriar índice simples (SEM unique)
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_requisicao_num
ON requisicao_compras(num_requisicao);

SELECT '✅ Índice SIMPLES criado em num_requisicao' as resultado;

-- =====================================================
-- PASSO 4: FK NÃO será recriada
-- =====================================================

-- Campo num_requisicao agora é apenas informativo
-- Não precisa de FK pois num_requisicao não é mais UNIQUE

SELECT '✅ FK não recriada (num_requisicao agora é informativo)' as resultado;

-- =====================================================
-- Verificar estado final
-- =====================================================

SELECT '========================================' as msg;
SELECT '📊 ESTADO FINAL' as msg;
SELECT '========================================' as msg;

-- Índices
SELECT indexname,
       CASE
           WHEN indexdef LIKE '%UNIQUE%' THEN '❌ UNIQUE'
           ELSE '✅ SIMPLES'
       END as tipo
FROM pg_indexes
WHERE tablename = 'requisicao_compras'
AND indexname LIKE '%num_requisicao%';

-- Constraints UNIQUE
SELECT '--- Constraints UNIQUE ---' as msg;

SELECT conname as constraint_name, pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'requisicao_compras'::regclass
AND contype = 'u'
ORDER BY conname;

-- Foreign Keys
SELECT '--- Foreign Keys em pedido_compras ---' as msg;

SELECT conname, confrelid::regclass as referencia_tabela
FROM pg_constraint
WHERE conrelid = 'pedido_compras'::regclass
AND contype = 'f'
AND conname LIKE '%num_requisicao%';

-- Mensagem final
SELECT '========================================' as msg;
SELECT '✅ CORREÇÃO CONCLUÍDA COM SUCESSO!' as msg;
SELECT '========================================' as msg;

SELECT 'ℹ️  Agora uma requisição pode ter MÚLTIPLAS LINHAS de produtos' as info;
SELECT 'ℹ️  UNIQUE está em: (num_requisicao + cod_produto) e (odoo_id)' as detalhe;
