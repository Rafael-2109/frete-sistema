-- =====================================================
-- Script para limpar nomes de produtos no HistoricoPedidos
-- Remove o código [XXX] do início do nome do produto
-- Data: 24/08/2025
-- =====================================================

-- psql $DATABASE_URL < migrations/limpar_nomes_produtos_historico.sql

-- Backup: Primeiro vamos verificar quantos registros serão afetados
SELECT COUNT(*) as total_registros_com_codigo
FROM historico_pedidos 
WHERE nome_produto LIKE '[%]%';

-- Visualizar alguns exemplos antes da alteração
SELECT 
    cod_produto,
    nome_produto as nome_antigo,
    CASE 
        WHEN nome_produto LIKE '[%]%' THEN 
            TRIM(SUBSTRING(nome_produto FROM POSITION(']' IN nome_produto) + 1))
        ELSE 
            nome_produto
    END as nome_novo
FROM historico_pedidos 
WHERE nome_produto LIKE '[%]%'
LIMIT 10;

-- =====================================================
-- EXECUTAR A ATUALIZAÇÃO
-- =====================================================

BEGIN;

-- Atualizar apenas registros que têm o padrão [codigo] no início
UPDATE historico_pedidos 
SET nome_produto = TRIM(SUBSTRING(nome_produto FROM POSITION(']' IN nome_produto) + 1))
WHERE nome_produto LIKE '[%]%'
  AND POSITION(']' IN nome_produto) > 0;

-- Verificar quantos registros foram atualizados
-- O PostgreSQL retorna automaticamente o número de linhas afetadas

-- Se tudo estiver OK, confirmar a transação
COMMIT;

-- Se algo der errado, reverter com:
-- ROLLBACK;

-- =====================================================
-- VERIFICAÇÃO PÓS-ATUALIZAÇÃO
-- =====================================================

-- Verificar se ainda existem registros com o padrão antigo
SELECT COUNT(*) as registros_restantes_com_codigo
FROM historico_pedidos 
WHERE nome_produto LIKE '[%]%';

-- Mostrar alguns exemplos dos registros atualizados
SELECT 
    cod_produto,
    nome_produto
FROM historico_pedidos 
WHERE nome_produto NOT LIKE '[%]%'
ORDER BY importado_em DESC
LIMIT 20;

-- =====================================================
-- ESTATÍSTICAS FINAIS
-- =====================================================

-- Resumo geral após a limpeza
SELECT 
    COUNT(*) as total_registros,
    COUNT(DISTINCT cod_produto) as produtos_unicos,
    COUNT(DISTINCT nome_produto) as nomes_unicos,
    MIN(data_pedido) as primeira_data,
    MAX(data_pedido) as ultima_data
FROM historico_pedidos;