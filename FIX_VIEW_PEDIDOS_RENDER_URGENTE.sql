-- =====================================================
-- FIX URGENTE: CRIAR VIEW PEDIDOS NO RENDER
-- Data: 2025-01-30
-- 
-- PROBLEMA: Pedidos não aparecem porque a VIEW não existe no Render
-- SOLUÇÃO: Criar VIEW que agrega dados de Separacao
-- =====================================================

-- 1. VERIFICAR SE A VIEW EXISTE
SELECT 'VERIFICANDO SE VIEW EXISTE...' as status;
SELECT EXISTS (
    SELECT FROM information_schema.views 
    WHERE table_name = 'pedidos'
) as view_exists;

-- 2. DROPAR VIEW SE EXISTIR (PARA RECRIAR LIMPO)
DROP VIEW IF EXISTS pedidos CASCADE;

-- 3. CRIAR VIEW PEDIDOS
-- Agrega dados de Separacao onde status != 'PREVISAO'
CREATE VIEW pedidos AS
SELECT 
    -- ID usando ROW_NUMBER (compatível com PostgreSQL)
    ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id)::integer as id,
    
    -- Identificador principal
    s.separacao_lote_id,
    MIN(s.num_pedido) as num_pedido,
    MIN(s.data_pedido) as data_pedido,
    
    -- Dados do cliente
    MIN(s.cnpj_cpf) as cnpj_cpf,
    MIN(s.raz_social_red) as raz_social_red,
    MIN(s.nome_cidade) as nome_cidade,
    MIN(s.cod_uf) as cod_uf,
    MIN(s.cidade_normalizada) as cidade_normalizada,
    MIN(s.uf_normalizada) as uf_normalizada,
    MIN(s.codigo_ibge) as codigo_ibge,
    
    -- Valores agregados (soma de todos os produtos do pedido)
    COALESCE(SUM(s.valor_saldo), 0) as valor_saldo_total,
    COALESCE(SUM(s.pallet), 0) as pallet_total,
    COALESCE(SUM(s.peso), 0) as peso_total,
    
    -- Rotas e observações
    MIN(s.rota) as rota,
    MIN(s.sub_rota) as sub_rota,
    MIN(s.observ_ped_1) as observ_ped_1,
    MIN(s.roteirizacao) as roteirizacao,
    
    -- Datas importantes
    MIN(s.expedicao) as expedicao,
    MIN(s.agendamento) as agendamento,
    MIN(s.protocolo) as protocolo,
    BOOL_OR(s.agendamento_confirmado) as agendamento_confirmado,
    
    -- Campos de transporte (NULL até ter cotação)
    NULL::varchar(100) as transportadora,
    NULL::float as valor_frete,
    NULL::float as valor_por_kg,
    NULL::varchar(100) as nome_tabela,
    NULL::varchar(50) as modalidade,
    NULL::varchar(100) as melhor_opcao,
    NULL::float as valor_melhor_opcao,
    NULL::integer as lead_time,
    
    -- Status e NF
    MIN(s.data_embarque) as data_embarque,
    MIN(s.numero_nf) as nf,
    MIN(s.status) as status,
    BOOL_OR(s.nf_cd) as nf_cd,
    MIN(s.pedido_cliente) as pedido_cliente,
    
    -- Controle de impressão
    BOOL_OR(s.separacao_impressa) as separacao_impressa,
    MIN(s.separacao_impressa_em) as separacao_impressa_em,
    MIN(s.separacao_impressa_por) as separacao_impressa_por,
    
    -- IDs relacionados
    MIN(s.cotacao_id) as cotacao_id,
    NULL::integer as usuario_id,
    MIN(s.criado_em) as criado_em

FROM separacao s
WHERE s.separacao_lote_id IS NOT NULL
  AND s.status != 'PREVISAO'  -- Exclui pré-separações
GROUP BY s.separacao_lote_id;

-- 4. VERIFICAR SE FUNCIONOU
SELECT 'VERIFICAÇÃO APÓS CRIAR VIEW:' as status;

-- Total de registros na tabela separacao
SELECT 'Total de registros em separacao' as info, COUNT(*) as total 
FROM separacao;

-- Registros elegíveis para a VIEW
SELECT 'Registros elegíveis (lote_id NOT NULL e status != PREVISAO)' as info, 
       COUNT(DISTINCT separacao_lote_id) as total_lotes,
       COUNT(*) as total_registros
FROM separacao 
WHERE separacao_lote_id IS NOT NULL 
  AND status != 'PREVISAO';

-- Total na VIEW pedidos
SELECT 'Total de pedidos na VIEW' as info, COUNT(*) as total 
FROM pedidos;

-- 5. EXEMPLOS DE PEDIDOS NA VIEW
SELECT 'PRIMEIROS 10 PEDIDOS NA VIEW:' as status;
SELECT 
    id,
    separacao_lote_id,
    num_pedido,
    cnpj_cpf,
    raz_social_red,
    cod_uf,
    status,
    expedicao,
    valor_saldo_total
FROM pedidos
ORDER BY expedicao DESC NULLS LAST
LIMIT 10;

-- 6. VERIFICAR PEDIDOS MAIS RECENTES
SELECT 'PEDIDOS COM EXPEDIÇÃO HOJE OU FUTURA:' as status;
SELECT 
    separacao_lote_id,
    num_pedido,
    raz_social_red,
    expedicao,
    status,
    nf_cd
FROM pedidos
WHERE expedicao >= CURRENT_DATE
ORDER BY expedicao
LIMIT 10;

-- 7. RESUMO FINAL
SELECT '===================' as separator;
SELECT 'RESUMO FINAL:' as status;
SELECT 
    'Total de pedidos na VIEW' as metrica,
    COUNT(*) as valor
FROM pedidos
UNION ALL
SELECT 
    'Pedidos ABERTOS' as metrica,
    COUNT(*) as valor
FROM pedidos
WHERE cotacao_id IS NULL 
  AND nf_cd = false
  AND (nf IS NULL OR nf = '')
UNION ALL
SELECT 
    'Pedidos com expedição >= hoje' as metrica,
    COUNT(*) as valor
FROM pedidos
WHERE expedicao >= CURRENT_DATE;

SELECT '===================' as separator;
SELECT 'VIEW CRIADA COM SUCESSO!' as status;
SELECT 'Agora os pedidos devem aparecer em /pedidos/lista_pedidos' as instrucao;