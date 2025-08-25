#!/bin/bash
# =====================================================
# Script para executar limpeza de nomes no Render
# Data: 24/08/2025
# =====================================================

echo "🔄 Iniciando limpeza de nomes de produtos no HistoricoPedidos..."
echo "=================================================="

# Executar o script SQL no banco de dados do Render
psql $DATABASE_URL << 'EOF'

-- =====================================================
-- VERIFICAÇÃO PRÉVIA
-- =====================================================
\echo '📊 Verificando registros que serão afetados...'

SELECT COUNT(*) as total_registros_com_codigo
FROM historico_pedidos 
WHERE nome_produto LIKE '[%]%';

\echo '📋 Exemplos de registros que serão limpos (máximo 5):'

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
LIMIT 5;

-- =====================================================
-- EXECUTAR A ATUALIZAÇÃO
-- =====================================================
\echo '🚀 Iniciando atualização dos nomes...'

BEGIN;

UPDATE historico_pedidos 
SET nome_produto = TRIM(SUBSTRING(nome_produto FROM POSITION(']' IN nome_produto) + 1))
WHERE nome_produto LIKE '[%]%'
  AND POSITION(']' IN nome_produto) > 0;

-- Mostrar quantos registros foram atualizados
GET DIAGNOSTICS;

COMMIT;

\echo '✅ Atualização concluída!'

-- =====================================================
-- VERIFICAÇÃO PÓS-ATUALIZAÇÃO
-- =====================================================
\echo '🔍 Verificando resultados...'

SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ Todos os nomes foram limpos com sucesso!'
        ELSE '⚠️ Ainda existem ' || COUNT(*) || ' registros com código'
    END as status
FROM historico_pedidos 
WHERE nome_produto LIKE '[%]%';

\echo '📊 Estatísticas finais:'

SELECT 
    COUNT(*) as total_registros,
    COUNT(DISTINCT cod_produto) as produtos_unicos,
    COUNT(DISTINCT nome_produto) as nomes_unicos
FROM historico_pedidos;

\echo '✨ Processo finalizado!'

EOF

echo "=================================================="
echo "✅ Script executado com sucesso!"