-- =====================================================
-- Script SQL para DROPAR tabela historico_requisicao_compras
-- Remove a tabela antiga antes de recriar com nova estrutura
-- Para execução no Shell do Render
-- =====================================================
-- Comando: psql $DATABASE_URL < scripts/dropar_tabela_historico_requisicoes.sql
-- =====================================================

-- Mostrar se a tabela existe
SELECT
    CASE
        WHEN EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'historico_requisicao_compras'
        )
        THEN '⚠️  Tabela historico_requisicao_compras EXISTE - Será removida'
        ELSE 'ℹ️  Tabela historico_requisicao_compras NÃO EXISTE - Nada a fazer'
    END as status;

-- Contar registros antes de dropar
SELECT
    COUNT(*) as total_registros_antes_drop,
    '⚠️  Estes registros serão PERDIDOS!' as aviso
FROM historico_requisicao_compras;

-- Dropar tabela e todos os índices/constraints associados
DROP TABLE IF EXISTS historico_requisicao_compras CASCADE;

-- Confirmar remoção
SELECT
    CASE
        WHEN NOT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'historico_requisicao_compras'
        )
        THEN '✅ Tabela historico_requisicao_compras REMOVIDA com sucesso!'
        ELSE '❌ ERRO: Tabela ainda existe'
    END as resultado;

-- Verificar índices órfãos (não deveria ter nenhum após CASCADE)
SELECT
    indexname,
    '⚠️  Índice órfão encontrado!' as alerta
FROM pg_indexes
WHERE tablename = 'historico_requisicao_compras';

-- =====================================================
-- Mensagem final
-- =====================================================
SELECT '✅ Script concluído! Agora você pode executar o script de criação.' as proximo_passo;
