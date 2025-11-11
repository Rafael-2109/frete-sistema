-- ==========================================================================================================
-- SCRIPT SQL PARA APAGAR TODOS OS DADOS DAS TABELAS DE COMPRAS
-- ⚠️  ATENÇÃO: ESTE SCRIPT REMOVE TODOS OS REGISTROS!
-- Execução: Render PostgreSQL Shell
-- ==========================================================================================================

-- ==========================================================================================================
-- PASSO 1: CONTAR REGISTROS ANTES DA EXCLUSÃO
-- ==========================================================================================================

SELECT 'CONTAGEM ANTES DA EXCLUSÃO' AS info;

SELECT
    'historico_pedido_compras' AS tabela,
    COUNT(*) AS total_registros
FROM historico_pedido_compras

UNION ALL

SELECT
    'historico_requisicao_compras' AS tabela,
    COUNT(*) AS total_registros
FROM historico_requisicao_compras

UNION ALL

SELECT
    'requisicao_compra_alocacao' AS tabela,
    COUNT(*) AS total_registros
FROM requisicao_compra_alocacao

UNION ALL

SELECT
    'pedido_compras' AS tabela,
    COUNT(*) AS total_registros
FROM pedido_compras

UNION ALL

SELECT
    'requisicao_compras' AS tabela,
    COUNT(*) AS total_registros
FROM requisicao_compras;


-- ==========================================================================================================
-- PASSO 2: DELETAR DADOS (ORDEM CORRETA - RESPEITANDO FKs)
-- ==========================================================================================================

-- ⚠️  ATENÇÃO: COMENTE AS LINHAS ABAIXO SE QUISER APENAS VISUALIZAR A CONTAGEM
-- ⚠️  DESCOMENTE PARA EXECUTAR A EXCLUSÃO

-- 1. Histórico de Pedidos (não tem FK)
-- DELETE FROM historico_pedido_compras;

-- 2. Histórico de Requisições (não tem FK)
-- DELETE FROM historico_requisicao_compras;

-- 3. Alocações (FK para requisição e pedido)
-- DELETE FROM requisicao_compra_alocacao;

-- 4. Pedidos de Compras
-- DELETE FROM pedido_compras;

-- 5. Requisições de Compras
-- DELETE FROM requisicao_compras;


-- ==========================================================================================================
-- PASSO 3: VERIFICAR EXCLUSÃO (APÓS EXECUTAR OS DELETEs)
-- ==========================================================================================================

/*
SELECT 'CONTAGEM APÓS EXCLUSÃO' AS info;

SELECT
    'historico_pedido_compras' AS tabela,
    COUNT(*) AS total_registros
FROM historico_pedido_compras

UNION ALL

SELECT
    'historico_requisicao_compras' AS tabela,
    COUNT(*) AS total_registros
FROM historico_requisicao_compras

UNION ALL

SELECT
    'requisicao_compra_alocacao' AS tabela,
    COUNT(*) AS total_registros
FROM requisicao_compra_alocacao

UNION ALL

SELECT
    'pedido_compras' AS tabela,
    COUNT(*) AS total_registros
FROM pedido_compras

UNION ALL

SELECT
    'requisicao_compras' AS tabela,
    COUNT(*) AS total_registros
FROM requisicao_compras;
*/


-- ==========================================================================================================
-- PASSO 4: RESETAR SEQUENCES (OPCIONAL - IDs VOLTAM PARA 1)
-- ==========================================================================================================

/*
-- Resetar sequences para começar do ID 1
ALTER SEQUENCE historico_pedido_compras_id_seq RESTART WITH 1;
ALTER SEQUENCE historico_requisicao_compras_id_seq RESTART WITH 1;
ALTER SEQUENCE requisicao_compra_alocacao_id_seq RESTART WITH 1;
ALTER SEQUENCE pedido_compras_id_seq RESTART WITH 1;
ALTER SEQUENCE requisicao_compras_id_seq RESTART WITH 1;
*/


-- ==========================================================================================================
-- 📋 INSTRUÇÕES DE USO
-- ==========================================================================================================

/*
1. PRIMEIRA EXECUÇÃO (apenas visualizar):
   - Execute PASSO 1 para ver quantos registros serão deletados

2. CONFIRMAR E EXECUTAR EXCLUSÃO:
   - Descomente as linhas do PASSO 2 (remova os -- no início)
   - Execute os DELETEs

3. VERIFICAR RESULTADO:
   - Descomente e execute o PASSO 3
   - Todas as tabelas devem mostrar 0 registros

4. RESETAR SEQUENCES (OPCIONAL):
   - Descomente e execute o PASSO 4
   - IDs recomeçarão do 1 na próxima inserção

5. PRÓXIMOS PASSOS:
   - Execute o script de migração: adicionar_company_id_compras_render.sql
   - Sincronize requisições manualmente (janela de 90 dias ou mais)
   - Sincronize pedidos manualmente (janela de 90 dias ou mais)
   - Sincronize alocações manualmente (janela de 90 dias ou mais)
*/


-- ==========================================================================================================
-- ✅ ORDEM DE EXECUÇÃO COMPLETA (COPIE E COLE TUDO DE UMA VEZ)
-- ==========================================================================================================

/*
-- DESCOMENTE TUDO ABAIXO PARA EXECUTAR TUDO DE UMA VEZ:

BEGIN;

-- Contar antes
SELECT 'ANTES' AS momento, 'historico_pedido_compras' AS tabela, COUNT(*) AS total FROM historico_pedido_compras
UNION ALL
SELECT 'ANTES', 'historico_requisicao_compras', COUNT(*) FROM historico_requisicao_compras
UNION ALL
SELECT 'ANTES', 'requisicao_compra_alocacao', COUNT(*) FROM requisicao_compra_alocacao
UNION ALL
SELECT 'ANTES', 'pedido_compras', COUNT(*) FROM pedido_compras
UNION ALL
SELECT 'ANTES', 'requisicao_compras', COUNT(*) FROM requisicao_compras;

-- Deletar
DELETE FROM historico_pedido_compras;
DELETE FROM historico_requisicao_compras;
DELETE FROM requisicao_compra_alocacao;
DELETE FROM pedido_compras;
DELETE FROM requisicao_compras;

-- Resetar sequences
ALTER SEQUENCE historico_pedido_compras_id_seq RESTART WITH 1;
ALTER SEQUENCE historico_requisicao_compras_id_seq RESTART WITH 1;
ALTER SEQUENCE requisicao_compra_alocacao_id_seq RESTART WITH 1;
ALTER SEQUENCE pedido_compras_id_seq RESTART WITH 1;
ALTER SEQUENCE requisicao_compras_id_seq RESTART WITH 1;

-- Contar depois
SELECT 'DEPOIS' AS momento, 'historico_pedido_compras' AS tabela, COUNT(*) AS total FROM historico_pedido_compras
UNION ALL
SELECT 'DEPOIS', 'historico_requisicao_compras', COUNT(*) FROM historico_requisicao_compras
UNION ALL
SELECT 'DEPOIS', 'requisicao_compra_alocacao', COUNT(*) FROM requisicao_compra_alocacao
UNION ALL
SELECT 'DEPOIS', 'pedido_compras', COUNT(*) FROM pedido_compras
UNION ALL
SELECT 'DEPOIS', 'requisicao_compras', COUNT(*) FROM requisicao_compras;

COMMIT;

-- ✅ Se tudo estiver OK, você verá:
-- ANTES: números > 0
-- DEPOIS: todos = 0

*/
