-- =====================================================
-- Script para LIMPAR TODOS os registros de HistoricoPedidos
-- ATENÇÃO: Isso apagará TODOS os dados da tabela!
-- Data: 24/08/2025
-- =====================================================

-- Verificar quantos registros serão apagados
SELECT COUNT(*) as total_registros_atuais
FROM historico_pedidos;

-- Mostrar alguns exemplos de registros que serão apagados
SELECT 
    id,
    num_pedido,
    cod_produto,
    nome_produto,
    data_pedido,
    importado_em
FROM historico_pedidos
ORDER BY id DESC
LIMIT 10;

-- =====================================================
-- EXECUTAR A LIMPEZA COMPLETA
-- =====================================================

BEGIN;

-- Apagar TODOS os registros
DELETE FROM historico_pedidos;

-- Resetar o contador de ID para começar do 1 novamente
ALTER SEQUENCE historico_pedidos_id_seq RESTART WITH 1;

-- Verificar que a tabela está vazia
SELECT COUNT(*) as registros_restantes FROM historico_pedidos;

-- Se tudo estiver OK, confirmar a transação
COMMIT;

-- Se algo der errado, reverter com:
-- ROLLBACK;

-- =====================================================
-- MENSAGEM FINAL
-- =====================================================
-- Após executar este script, você pode reimportar
-- os dados do Odoo com o mapeamento corrigido
-- que usa default_code em vez do ID interno