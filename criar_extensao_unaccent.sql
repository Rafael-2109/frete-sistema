-- =====================================
-- CRIAR EXTENSÃO UNACCENT NO POSTGRESQL
-- Execute no shell do Render: psql $DATABASE_URL
-- =====================================

-- Criar extensão para remover acentos
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Testar se funcionou
SELECT unaccent('José São Paulo AÇÃO') AS teste;
-- Deve retornar: Jose Sao Paulo ACAO

-- Criar índices otimizados para buscas sem acento
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_raz_social_unaccent
ON carteira_principal(lower(unaccent(raz_social)))
WHERE raz_social IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_raz_social_red_unaccent
ON carteira_principal(lower(unaccent(raz_social_red)))
WHERE raz_social_red IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_pedido_cliente_unaccent
ON carteira_principal(lower(unaccent(pedido_cliente)))
WHERE pedido_cliente IS NOT NULL;

-- Verificar se os índices foram criados
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'carteira_principal'
AND indexname LIKE '%unaccent%';