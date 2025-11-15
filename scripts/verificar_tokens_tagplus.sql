-- ============================================================================
-- SCRIPT SQL: Verificar Tokens TagPlus no Banco de Dados
-- ============================================================================
-- Execute este script no shell do Render para verificar os tokens OAuth2
--
-- Como executar no Render:
-- 1. Dashboard → Shell
-- 2. Conectar ao PostgreSQL: psql $DATABASE_URL
-- 3. Copiar e colar este script
-- ============================================================================

\echo '════════════════════════════════════════════════════════════════════════════'
\echo '🔍 VERIFICAÇÃO DE TOKENS TAGPLUS NO BANCO DE DADOS'
\echo '════════════════════════════════════════════════════════════════════════════'
\echo ''

-- ============================================================================
-- 1. VERIFICAR SE TABELA EXISTS
-- ============================================================================
\echo '📋 1. Verificando se tabela tagplus_oauth_token existe...'
\echo ''

SELECT
    CASE
        WHEN EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'tagplus_oauth_token'
        )
        THEN '✅ Tabela tagplus_oauth_token encontrada'
        ELSE '❌ ERRO: Tabela tagplus_oauth_token NÃO EXISTE! Execute migrations.'
    END as status;

\echo ''

-- ============================================================================
-- 2. CONTAR TOKENS
-- ============================================================================
\echo '📊 2. Contando tokens no banco...'
\echo ''

SELECT
    COUNT(*) as total_tokens,
    COUNT(CASE WHEN ativo = true THEN 1 END) as tokens_ativos,
    COUNT(CASE WHEN ativo = false THEN 1 END) as tokens_inativos
FROM tagplus_oauth_token;

\echo ''

-- ============================================================================
-- 3. LISTAR TODOS OS TOKENS (RESUMO)
-- ============================================================================
\echo '📋 3. Listando todos os tokens (resumo)...'
\echo ''

SELECT
    id,
    api_type as "Tipo API",
    CASE
        WHEN ativo = true THEN '✅ Ativo'
        ELSE '❌ Inativo'
    END as "Status",
    CASE
        WHEN expires_at > NOW() THEN '✅ Válido'
        WHEN expires_at <= NOW() THEN '⚠️  Expirado'
        ELSE '❓ Sem expiração'
    END as "Validade",
    to_char(expires_at, 'DD/MM/YYYY HH24:MI') as "Expira em",
    total_refreshes as "Renovações",
    to_char(ultimo_refresh, 'DD/MM/YYYY HH24:MI') as "Última Renovação",
    to_char(ultima_requisicao, 'DD/MM/YYYY HH24:MI') as "Última Uso"
FROM tagplus_oauth_token
ORDER BY id;

\echo ''

-- ============================================================================
-- 4. DETALHES COMPLETOS DOS TOKENS
-- ============================================================================
\echo '🔍 4. Detalhes completos dos tokens...'
\echo ''

SELECT
    id as "ID",
    api_type as "Tipo API",

    -- Access Token (primeiros 40 e últimos 10 caracteres)
    CASE
        WHEN access_token IS NOT NULL AND access_token != '' THEN
            CONCAT(
                SUBSTRING(access_token, 1, 40),
                '...',
                SUBSTRING(access_token FROM LENGTH(access_token) - 9)
            )
        ELSE '❌ VAZIO'
    END as "Access Token (preview)",

    -- Refresh Token (primeiros 40 e últimos 10 caracteres)
    CASE
        WHEN refresh_token IS NOT NULL AND refresh_token != '' THEN
            CONCAT(
                SUBSTRING(refresh_token, 1, 40),
                '...',
                SUBSTRING(refresh_token FROM LENGTH(refresh_token) - 9)
            )
        ELSE '❌ VAZIO'
    END as "Refresh Token (preview)",

    -- Tempo até expiração
    CASE
        WHEN expires_at > NOW() THEN
            CONCAT(
                EXTRACT(HOUR FROM (expires_at - NOW())), 'h ',
                EXTRACT(MINUTE FROM (expires_at - NOW())), 'm'
            )
        WHEN expires_at <= NOW() THEN
            CONCAT(
                '⚠️  Expirado há ',
                EXTRACT(HOUR FROM (NOW() - expires_at)), 'h ',
                EXTRACT(MINUTE FROM (NOW() - expires_at)), 'm'
            )
        ELSE 'Sem expiração definida'
    END as "Tempo Restante/Expirado",

    ativo as "Ativo",
    token_type as "Tipo",
    total_refreshes as "Total Renovações"
FROM tagplus_oauth_token
ORDER BY id;

\echo ''

-- ============================================================================
-- 5. VERIFICAR EXPIRAÇÃO
-- ============================================================================
\echo '⏰ 5. Verificando expiração dos tokens...'
\echo ''

SELECT
    api_type as "Tipo API",
    expires_at as "Data Expiração",
    NOW() as "Agora (UTC)",
    CASE
        WHEN expires_at > NOW() + INTERVAL '1 hour' THEN
            '✅ Válido (>1h restante)'
        WHEN expires_at > NOW() THEN
            '⚠️  Expira em breve (<1h)'
        WHEN expires_at <= NOW() THEN
            '❌ EXPIRADO'
        ELSE
            '❓ Sem data de expiração'
    END as "Status Expiração",
    CASE
        WHEN expires_at > NOW() THEN
            CONCAT(
                EXTRACT(HOUR FROM (expires_at - NOW())), 'h ',
                EXTRACT(MINUTE FROM (expires_at - NOW())), 'm restantes'
            )
        WHEN expires_at <= NOW() THEN
            CONCAT(
                'Expirado há ',
                EXTRACT(HOUR FROM (NOW() - expires_at)), 'h ',
                EXTRACT(MINUTE FROM (NOW() - expires_at)), 'm'
            )
        ELSE
            'N/A'
    END as "Tempo"
FROM tagplus_oauth_token
WHERE ativo = true
ORDER BY expires_at;

\echo ''

-- ============================================================================
-- 6. ESTATÍSTICAS DE USO
-- ============================================================================
\echo '📊 6. Estatísticas de uso dos tokens...'
\echo ''

SELECT
    api_type as "Tipo API",
    total_refreshes as "Renovações Feitas",
    CASE
        WHEN ultimo_refresh IS NOT NULL THEN
            to_char(ultimo_refresh, 'DD/MM/YYYY HH24:MI:SS')
        ELSE
            'Nunca renovado'
    END as "Última Renovação",
    CASE
        WHEN ultima_requisicao IS NOT NULL THEN
            to_char(ultima_requisicao, 'DD/MM/YYYY HH24:MI:SS')
        ELSE
            'Nunca usado'
    END as "Último Uso",
    to_char(criado_em, 'DD/MM/YYYY HH24:MI:SS') as "Criado Em",
    to_char(atualizado_em, 'DD/MM/YYYY HH24:MI:SS') as "Atualizado Em"
FROM tagplus_oauth_token
WHERE ativo = true
ORDER BY api_type;

\echo ''

-- ============================================================================
-- 7. DIAGNÓSTICO E RECOMENDAÇÕES
-- ============================================================================
\echo '🔧 7. Diagnóstico e recomendações...'
\echo ''

WITH diagnostico AS (
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN ativo = true AND expires_at > NOW() THEN 1 END) as validos,
        COUNT(CASE WHEN ativo = true AND expires_at <= NOW() THEN 1 END) as expirados,
        COUNT(CASE WHEN ativo = false THEN 1 END) as inativos,
        COUNT(CASE WHEN access_token IS NULL OR access_token = '' THEN 1 END) as sem_access_token,
        COUNT(CASE WHEN refresh_token IS NULL OR refresh_token = '' THEN 1 END) as sem_refresh_token
    FROM tagplus_oauth_token
)
SELECT
    total as "Total de Tokens",
    validos as "✅ Válidos",
    expirados as "⚠️  Expirados",
    inativos as "❌ Inativos",
    sem_access_token as "❌ Sem Access Token",
    sem_refresh_token as "⚠️  Sem Refresh Token",
    CASE
        WHEN validos > 0 THEN
            '👍 Sistema OK - Tokens válidos encontrados'
        WHEN expirados > 0 THEN
            '⚠️  ATENÇÃO - Tokens expirados (serão renovados automaticamente)'
        WHEN total = 0 THEN
            '❌ ERRO - Nenhum token no banco! Autorize em /tagplus/oauth/authorize'
        ELSE
            '❌ PROBLEMA - Tokens inválidos ou inativos'
    END as "Diagnóstico"
FROM diagnostico;

\echo ''
\echo '════════════════════════════════════════════════════════════════════════════'
\echo '✅ Verificação concluída!'
\echo '════════════════════════════════════════════════════════════════════════════'
\echo ''
\echo '📝 AÇÕES RECOMENDADAS:'
\echo ''
\echo 'Se não houver tokens válidos:'
\echo '1. Autorizar API Clientes: /tagplus/oauth/authorize/cliente'
\echo '2. Autorizar API Notas: /tagplus/oauth/authorize/nfe'
\echo ''
\echo 'Se tokens expirados:'
\echo '→ O sistema renova automaticamente se houver refresh_token'
\echo '→ Se falhar, autorize novamente (links acima)'
\echo ''
