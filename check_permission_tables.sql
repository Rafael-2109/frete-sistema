-- ============================================
-- SCRIPT DE VERIFICAÇÃO DAS TABELAS DE PERMISSÃO
-- Para executar no Render Database Shell
-- ============================================

-- 1. Verificar se as tabelas existem
SELECT 
    table_name,
    CASE 
        WHEN table_name IS NOT NULL THEN '✅ Existe'
        ELSE '❌ Não existe'
    END as status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'permission_category',
    'permission_module',
    'permission_submodule',
    'user_permission',
    'vendedor',
    'equipe_vendas',
    'user_vendedor',
    'user_equipe',
    'vendedor_permission',
    'equipe_permission',
    'permission_template',
    'perfil_usuario',
    'permission_log',
    'batch_operation',
    'permission_cache'
)
ORDER BY table_name;

-- 2. Mostrar colunas da tabela permission_module (se existir)
SELECT 
    '=== COLUNAS DE permission_module ===' as info;
    
SELECT 
    ordinal_position as pos,
    column_name as coluna,
    data_type as tipo,
    is_nullable as permite_null,
    column_default as valor_padrao
FROM information_schema.columns 
WHERE table_name = 'permission_module'
AND table_schema = 'public'
ORDER BY ordinal_position;

-- 3. Mostrar colunas da tabela permission_category (se existir)
SELECT 
    '=== COLUNAS DE permission_category ===' as info;
    
SELECT 
    ordinal_position as pos,
    column_name as coluna,
    data_type as tipo,
    is_nullable as permite_null,
    column_default as valor_padrao
FROM information_schema.columns 
WHERE table_name = 'permission_category'
AND table_schema = 'public'
ORDER BY ordinal_position;

-- 4. Mostrar colunas da tabela permission_submodule (se existir)
SELECT 
    '=== COLUNAS DE permission_submodule ===' as info;
    
SELECT 
    ordinal_position as pos,
    column_name as coluna,
    data_type as tipo,
    is_nullable as permite_null,
    column_default as valor_padrao
FROM information_schema.columns 
WHERE table_name = 'permission_submodule'
AND table_schema = 'public'
ORDER BY ordinal_position;

-- 5. Mostrar colunas da tabela user_permission (se existir)
SELECT 
    '=== COLUNAS DE user_permission ===' as info;
    
SELECT 
    ordinal_position as pos,
    column_name as coluna,
    data_type as tipo,
    is_nullable as permite_null,
    column_default as valor_padrao
FROM information_schema.columns 
WHERE table_name = 'user_permission'
AND table_schema = 'public'
ORDER BY ordinal_position;

-- 6. Verificar dados existentes em permission_module
SELECT 
    '=== DADOS EM permission_module ===' as info;

SELECT 
    COUNT(*) as total_registros
FROM permission_module;

-- 7. Listar primeiros registros de permission_module (se houver)
SELECT 
    id,
    category_id,
    CASE 
        WHEN column_name = 'nome' THEN nome
        WHEN column_name = 'name' THEN name
        ELSE 'N/A'
    END as nome_coluna,
    CASE 
        WHEN column_name = 'ativo' THEN ativo
        WHEN column_name = 'active' THEN active
        ELSE true
    END as ativo_status
FROM permission_module, 
     (SELECT column_name 
      FROM information_schema.columns 
      WHERE table_name = 'permission_module' 
      AND column_name IN ('nome', 'name')
      LIMIT 1) as col
LIMIT 5;

-- 8. Identificar problemas de nomenclatura
SELECT 
    '=== ANÁLISE DE PROBLEMAS ===' as info;

SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'permission_module' 
            AND column_name = 'name'
        ) THEN '⚠️ PROBLEMA: Coluna "name" existe (deveria ser "nome")'
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'permission_module' 
            AND column_name = 'nome'
        ) THEN '✅ OK: Coluna "nome" existe'
        ELSE '❌ ERRO: Nem "name" nem "nome" existem'
    END as status_permission_module,
    
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'permission_module' 
            AND column_name = 'display_name'
        ) THEN '⚠️ PROBLEMA: Coluna "display_name" existe (deveria ser "nome_exibicao")'
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'permission_module' 
            AND column_name = 'nome_exibicao'
        ) THEN '✅ OK: Coluna "nome_exibicao" existe'
        ELSE '❌ ERRO: Nem "display_name" nem "nome_exibicao" existem'
    END as status_nome_exibicao;

-- 9. Verificar migrações aplicadas
SELECT 
    '=== MIGRAÇÕES APLICADAS ===' as info;

SELECT 
    version_num as versao,
    SUBSTRING(version_num, 1, 12) || '...' as versao_curta
FROM alembic_version
ORDER BY version_num DESC
LIMIT 5;

-- 10. Resumo final
SELECT 
    '=== RESUMO ===' as info;

SELECT 
    'Total de tabelas de permissão existentes' as metrica,
    COUNT(*) as valor
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'permission%'
OR table_name LIKE '%vendedor%'
OR table_name LIKE '%equipe%';