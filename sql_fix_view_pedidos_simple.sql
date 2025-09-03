-- =====================================================
-- VIEW PEDIDOS ULTRA SIMPLES - MÁXIMA COMPATIBILIDADE
-- Data: 2025-01-30
-- 
-- Versão mais simples possível para funcionar em qualquer PostgreSQL
-- =====================================================

-- 1. DROPAR VIEW SE EXISTIR
DROP VIEW IF EXISTS pedidos CASCADE;

-- 2. CRIAR VIEW COM ID USANDO ROW_NUMBER (mais compatível)
CREATE VIEW pedidos AS
SELECT 
    -- ID usando ROW_NUMBER que sempre funciona
    ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id) AS id,
    
    -- Campos básicos
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
    
    -- Valores agregados
    COALESCE(SUM(s.valor_saldo), 0) as valor_saldo_total,
    COALESCE(SUM(s.pallet), 0) as pallet_total,
    COALESCE(SUM(s.peso), 0) as peso_total,
    
    -- Outros campos
    MIN(s.rota) as rota,
    MIN(s.sub_rota) as sub_rota,
    MIN(s.observ_ped_1) as observ_ped_1,
    MIN(s.roteirizacao) as roteirizacao,
    MIN(s.expedicao) as expedicao,
    MIN(s.agendamento) as agendamento,
    MIN(s.protocolo) as protocolo,
    BOOL_OR(s.agendamento_confirmado) as agendamento_confirmado,
    
    -- Campos NULL para compatibilidade
    NULL as transportadora,
    NULL::float as valor_frete,
    NULL::float as valor_por_kg,
    NULL as nome_tabela,
    NULL as modalidade,
    NULL as melhor_opcao,
    NULL::float as valor_melhor_opcao,
    NULL::integer as lead_time,
    
    -- Status
    MIN(s.data_embarque) as data_embarque,
    MIN(s.numero_nf) as nf,
    MIN(s.status) as status,
    BOOL_OR(s.nf_cd) as nf_cd,
    MIN(s.pedido_cliente) as pedido_cliente,
    
    -- Impressão
    BOOL_OR(s.separacao_impressa) as separacao_impressa,
    MIN(s.separacao_impressa_em) as separacao_impressa_em,
    MIN(s.separacao_impressa_por) as separacao_impressa_por,
    
    -- IDs relacionados
    MIN(s.cotacao_id) as cotacao_id,
    NULL::integer as usuario_id,
    MIN(s.criado_em) as criado_em

FROM separacao s
WHERE s.separacao_lote_id IS NOT NULL
  AND s.status <> 'PREVISAO'  -- Usando <> em vez de !=
GROUP BY s.separacao_lote_id;

-- 3. DEBUG: Verificar o que está acontecendo
SELECT 'DEBUG: Total separações na tabela' as info, COUNT(*) as total 
FROM separacao;

SELECT 'DEBUG: Separações com lote_id NOT NULL' as info, COUNT(*) as total 
FROM separacao 
WHERE separacao_lote_id IS NOT NULL;

SELECT 'DEBUG: Separações com status != PREVISAO' as info, COUNT(*) as total 
FROM separacao 
WHERE status <> 'PREVISAO';

SELECT 'DEBUG: Separações que atendem ambos critérios' as info, COUNT(DISTINCT separacao_lote_id) as total 
FROM separacao 
WHERE separacao_lote_id IS NOT NULL 
  AND status <> 'PREVISAO';

SELECT 'DEBUG: Total na VIEW pedidos' as info, COUNT(*) as total 
FROM pedidos;

-- 4. Mostrar alguns exemplos
SELECT 'EXEMPLOS DE SEPARAÇÕES QUE DEVERIAM APARECER:' as info;
SELECT separacao_lote_id, num_pedido, status, sincronizado_nf
FROM separacao
WHERE separacao_lote_id IS NOT NULL 
  AND status <> 'PREVISAO'
LIMIT 5;