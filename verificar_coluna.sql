-- Script SQL para verificar a implementação da coluna data_expedicao_editada
-- Execute este script no seu banco PostgreSQL

-- 1. Verificar se a tabela existe
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename = 'pre_separacao_item';

-- 2. Verificar estrutura da tabela
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'pre_separacao_item'
ORDER BY ordinal_position;

-- 3. Verificar especificamente a coluna data_expedicao_editada
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pre_separacao_item' 
    AND column_name = 'data_expedicao_editada';

-- 4. Verificar constraints da tabela
SELECT 
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'pre_separacao_item'
ORDER BY tc.constraint_type, kcu.ordinal_position;

-- 5. Verificar constraint única específica
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conrelid = 'pre_separacao_item'::regclass
    AND conname = 'uq_pre_separacao_contexto_unico';

-- 6. Verificar índices da tabela
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'pre_separacao_item'
ORDER BY indexname;

-- 7. Verificar se há dados na tabela
SELECT COUNT(*) as total_registros
FROM pre_separacao_item;

-- 8. Verificar dados com data_expedicao_editada NULL (se houver dados)
SELECT 
    COUNT(*) as registros_com_null,
    COUNT(*) FILTER (WHERE data_expedicao_editada IS NOT NULL) as registros_com_data
FROM pre_separacao_item;

-- 9. Exemplo de alguns registros (limitado a 5)
SELECT 
    id,
    num_pedido,
    cod_produto,
    data_expedicao_editada,
    data_criacao
FROM pre_separacao_item
ORDER BY data_criacao DESC
LIMIT 5;

-- 10. Verificar se a constraint está funcionando (teste)
-- DESCOMENTE APENAS PARA TESTE:
-- INSERT INTO pre_separacao_item (
--     num_pedido, cod_produto, qtd_original_carteira, 
--     qtd_selecionada_usuario, qtd_restante_calculada,
--     data_expedicao_editada, criado_por
-- ) VALUES (
--     'TESTE001', 'PROD001', 100.0, 50.0, 50.0,
--     CURRENT_DATE, 'TESTE_SISTEMA'
-- );

-- Para remover o teste:
-- DELETE FROM pre_separacao_item WHERE num_pedido = 'TESTE001';