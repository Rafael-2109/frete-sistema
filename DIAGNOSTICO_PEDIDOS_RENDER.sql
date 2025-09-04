-- =====================================================
-- DIAGNÓSTICO: POR QUE PEDIDOS NÃO APARECEM NO RENDER?
-- Data: 2025-01-30
-- =====================================================

-- 1. VERIFICAR SE A VIEW EXISTE
SELECT '=== 1. VIEW PEDIDOS EXISTE? ===' as etapa;
SELECT EXISTS (
    SELECT FROM information_schema.views 
    WHERE table_name = 'pedidos'
) as view_pedidos_existe;

-- 2. VERIFICAR ESTRUTURA DA VIEW
SELECT '=== 2. ESTRUTURA DA VIEW PEDIDOS ===' as etapa;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'pedidos'
ORDER BY ordinal_position
LIMIT 10;

-- 3. VERIFICAR DADOS NA TABELA SEPARACAO
SELECT '=== 3. DADOS NA TABELA SEPARACAO ===' as etapa;
SELECT 
    COUNT(*) as total_registros,
    COUNT(DISTINCT separacao_lote_id) as total_lotes,
    COUNT(DISTINCT num_pedido) as total_pedidos,
    COUNT(CASE WHEN status = 'PREVISAO' THEN 1 END) as total_previsao,
    COUNT(CASE WHEN status != 'PREVISAO' THEN 1 END) as total_nao_previsao,
    COUNT(CASE WHEN separacao_lote_id IS NULL THEN 1 END) as lotes_null,
    COUNT(CASE WHEN separacao_lote_id IS NOT NULL THEN 1 END) as lotes_validos
FROM separacao;

-- 4. VALORES DE STATUS ÚNICOS
SELECT '=== 4. VALORES ÚNICOS DE STATUS ===' as etapa;
SELECT DISTINCT status, COUNT(*) as quantidade
FROM separacao
GROUP BY status
ORDER BY quantidade DESC;

-- 5. VERIFICAR REGISTROS ELEGÍVEIS PARA A VIEW
SELECT '=== 5. REGISTROS ELEGÍVEIS (separacao_lote_id NOT NULL e status != PREVISAO) ===' as etapa;
SELECT 
    COUNT(*) as registros_elegiveis,
    COUNT(DISTINCT separacao_lote_id) as lotes_elegiveis
FROM separacao
WHERE separacao_lote_id IS NOT NULL 
  AND status != 'PREVISAO';

-- 6. EXEMPLOS DE REGISTROS ELEGÍVEIS
SELECT '=== 6. EXEMPLOS DE REGISTROS QUE DEVERIAM APARECER ===' as etapa;
SELECT 
    separacao_lote_id,
    num_pedido,
    status,
    cnpj_cpf,
    raz_social_red,
    expedicao,
    sincronizado_nf,
    nf_cd
FROM separacao
WHERE separacao_lote_id IS NOT NULL 
  AND status != 'PREVISAO'
ORDER BY criado_em DESC
LIMIT 10;

-- 7. VERIFICAR DADOS NA VIEW PEDIDOS
SELECT '=== 7. DADOS NA VIEW PEDIDOS ===' as etapa;
SELECT COUNT(*) as total_pedidos_na_view
FROM pedidos;

-- 8. SE HÁ DADOS, MOSTRAR EXEMPLOS
SELECT '=== 8. EXEMPLOS DE PEDIDOS NA VIEW (SE EXISTIREM) ===' as etapa;
SELECT 
    id,
    separacao_lote_id,
    num_pedido,
    status,
    expedicao,
    nf_cd
FROM pedidos
LIMIT 10;

-- 9. VERIFICAR PEDIDOS COM EXPEDIÇÃO RECENTE
SELECT '=== 9. PEDIDOS COM EXPEDIÇÃO >= HOJE-7 DIAS ===' as etapa;
SELECT 
    COUNT(*) as pedidos_recentes
FROM pedidos
WHERE expedicao >= CURRENT_DATE - INTERVAL '7 days';

-- 10. VERIFICAR SE HÁ PROBLEMA COM CASE SENSITIVE NO STATUS
SELECT '=== 10. VERIFICAR VARIAÇÕES DE CASE NO STATUS ===' as etapa;
SELECT 
    status,
    UPPER(status) as status_upper,
    LOWER(status) as status_lower,
    COUNT(*) as quantidade
FROM separacao
WHERE status IS NOT NULL
GROUP BY status
ORDER BY quantidade DESC
LIMIT 20;

-- 11. TESTAR QUERY DIRETA (SIMULANDO A VIEW)
SELECT '=== 11. TESTAR QUERY DIRETA (MESMO SQL DA VIEW) ===' as etapa;
SELECT COUNT(*) as total_query_direta
FROM (
    SELECT 
        ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id)::integer as id,
        s.separacao_lote_id,
        MIN(s.num_pedido) as num_pedido
    FROM separacao s
    WHERE s.separacao_lote_id IS NOT NULL
      AND s.status != 'PREVISAO'
    GROUP BY s.separacao_lote_id
) as teste;

-- 12. VERIFICAR SE STATUS TEM ESPAÇOS OU CARACTERES INVISÍVEIS
SELECT '=== 12. STATUS COM ESPAÇOS OU CARACTERES ESTRANHOS ===' as etapa;
SELECT 
    '|' || status || '|' as status_com_delimitadores,
    LENGTH(status) as tamanho,
    COUNT(*) as quantidade
FROM separacao
WHERE status LIKE '%PREVISAO%' 
   OR status LIKE '% %'
   OR LENGTH(status) != LENGTH(TRIM(status))
GROUP BY status
ORDER BY quantidade DESC;

-- 13. CONTAR REGISTROS POR CONDIÇÃO
SELECT '=== 13. BREAKDOWN POR CONDIÇÃO ===' as etapa;
SELECT 
    'Total em separacao' as condicao, COUNT(*) as quantidade
FROM separacao
UNION ALL
SELECT 
    'Com separacao_lote_id NOT NULL' as condicao, COUNT(*) as quantidade
FROM separacao WHERE separacao_lote_id IS NOT NULL
UNION ALL
SELECT 
    'Com status != PREVISAO' as condicao, COUNT(*) as quantidade
FROM separacao WHERE status != 'PREVISAO'
UNION ALL
SELECT 
    'Ambas condições (elegíveis)' as condicao, COUNT(*) as quantidade
FROM separacao WHERE separacao_lote_id IS NOT NULL AND status != 'PREVISAO'
UNION ALL
SELECT 
    'Com sincronizado_nf = false' as condicao, COUNT(*) as quantidade
FROM separacao WHERE sincronizado_nf = false
UNION ALL
SELECT 
    'Elegíveis + sincronizado_nf = false' as condicao, COUNT(*) as quantidade
FROM separacao 
WHERE separacao_lote_id IS NOT NULL 
  AND status != 'PREVISAO'
  AND sincronizado_nf = false;

-- 14. RESULTADO FINAL
SELECT '=== 14. RESUMO DO DIAGNÓSTICO ===' as etapa;
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM pedidos) > 0 THEN 
            'VIEW TEM DADOS - Problema deve ser no frontend ou filtros da aplicação'
        WHEN (SELECT COUNT(*) FROM separacao WHERE separacao_lote_id IS NOT NULL AND status != 'PREVISAO') > 0 THEN
            'TEM DADOS ELEGÍVEIS MAS VIEW ESTÁ VAZIA - Problema na criação da VIEW'
        ELSE
            'NÃO HÁ DADOS ELEGÍVEIS - Verificar se separacao tem dados corretos'
    END as diagnostico;

-- RECRIAR VIEW COM ID CORRIGIDO - VERSÃO POSTGRESQL
DROP VIEW IF EXISTS pedidos CASCADE;

CREATE VIEW pedidos AS
SELECT
    -- Usar hash do lote_id para ID único (PostgreSQL)
    ('x' || substring(md5(s.separacao_lote_id::text), 1,8))::bit(32)::int as id,
    s.separacao_lote_id,
    MIN(s.num_pedido) as num_pedido,
    MIN(s.data_pedido) as data_pedido,
    MIN(s.cnpj_cpf) as cnpj_cpf,
    MIN(s.raz_social_red) as raz_social_red,
    MIN(s.nome_cidade) as nome_cidade,
    MIN(s.cod_uf) as cod_uf,
    MIN(s.cidade_normalizada) as cidade_normalizada,
    MIN(s.uf_normalizada) as uf_normalizada,
    MIN(s.codigo_ibge) as codigo_ibge,
    COALESCE(SUM(s.valor_saldo), 0) as valor_saldo_total,
    COALESCE(SUM(s.pallet), 0) as pallet_total,
    COALESCE(SUM(s.peso), 0) as peso_total,
    MIN(s.rota) as rota,
    MIN(s.sub_rota) as sub_rota,
    MIN(s.observ_ped_1) as observ_ped_1,
    MIN(s.roteirizacao) as roteirizacao,
    MIN(s.expedicao) as expedicao,
    MIN(s.agendamento) as agendamento,
    MIN(s.protocolo) as protocolo,
    BOOL_OR(s.agendamento_confirmado) as agendamento_confirmado,
    NULL::varchar(100) as transportadora,
    NULL::float as valor_frete,
    NULL::float as valor_por_kg,
    NULL::varchar(100) as nome_tabela,
    NULL::varchar(50) as modalidade,
    NULL::varchar(100) as melhor_opcao,
    NULL::float as valor_melhor_opcao,
    NULL::integer as lead_time,
    MIN(s.data_embarque) as data_embarque,
    MIN(s.numero_nf) as nf,
    MIN(s.status) as status,
    BOOL_OR(s.nf_cd) as nf_cd,
    MIN(s.pedido_cliente) as pedido_cliente,
    BOOL_OR(s.separacao_impressa) as separacao_impressa,
    MIN(s.separacao_impressa_em) as separacao_impressa_em,
    MIN(s.separacao_impressa_por) as separacao_impressa_por,
    MIN(s.cotacao_id) as cotacao_id,
    NULL::integer as usuario_id,
    MIN(s.criado_em) as criado_em
FROM separacao s
WHERE s.separacao_lote_id IS NOT NULL
AND s.status != 'PREVISAO'
GROUP BY s.separacao_lote_id;

-- VERIFICAR RESULTADO
SELECT COUNT(*) as total_pedidos FROM pedidos;
SELECT COUNT(*) as pedidos_abertos
FROM pedidos
WHERE cotacao_id IS NULL
    AND nf_cd = false
    AND (nf IS NULL OR nf = '');