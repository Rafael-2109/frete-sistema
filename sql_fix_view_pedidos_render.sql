-- =====================================================
-- FIX VIEW PEDIDOS PARA RENDER (PostgreSQL)
-- Data: 2025-01-30
-- 
-- Versão simplificada e compatível com PostgreSQL
-- =====================================================

-- 1. VERIFICAR SE A VIEW EXISTE E DROPAR
DROP VIEW IF EXISTS pedidos CASCADE;

-- 2. CRIAR VIEW COM ID SIMPLIFICADO
CREATE VIEW pedidos AS
SELECT 
    -- ID simplificado usando hashtext (mais confiável no PostgreSQL)
    -- Se hashtext não existir, usar alternativa
    CASE 
        WHEN s.separacao_lote_id IS NOT NULL THEN 
            ABS(hashtext(s.separacao_lote_id))
        ELSE 
            0
    END as id,
    
    -- Identificador único
    s.separacao_lote_id,
    MIN(s.num_pedido) as num_pedido,
    MIN(s.data_pedido) as data_pedido,
    
    -- Cliente (primeiro registro do grupo)
    MIN(s.cnpj_cpf) as cnpj_cpf,
    MIN(s.raz_social_red) as raz_social_red,
    MIN(s.nome_cidade) as nome_cidade,
    MIN(s.cod_uf) as cod_uf,
    
    -- Campos normalizados
    MIN(s.cidade_normalizada) as cidade_normalizada,
    MIN(s.uf_normalizada) as uf_normalizada,
    MIN(s.codigo_ibge) as codigo_ibge,
    
    -- Agregações de valores (SOMA dos produtos)
    COALESCE(SUM(s.valor_saldo), 0) as valor_saldo_total,
    COALESCE(SUM(s.pallet), 0) as pallet_total,
    COALESCE(SUM(s.peso), 0) as peso_total,
    
    -- Rota e observações
    MIN(s.rota) as rota,
    MIN(s.sub_rota) as sub_rota,
    MIN(s.observ_ped_1) as observ_ped_1,
    MIN(s.roteirizacao) as roteirizacao,
    
    -- Datas importantes
    MIN(s.expedicao) as expedicao,
    MIN(s.agendamento) as agendamento,
    MIN(s.protocolo) as protocolo,
    BOOL_OR(s.agendamento_confirmado) as agendamento_confirmado,
    
    -- Campos de transporte
    CAST(NULL AS varchar(100)) as transportadora,
    CAST(NULL AS float) as valor_frete,
    CAST(NULL AS float) as valor_por_kg,
    CAST(NULL AS varchar(100)) as nome_tabela,
    CAST(NULL AS varchar(50)) as modalidade,
    CAST(NULL AS varchar(100)) as melhor_opcao,
    CAST(NULL AS float) as valor_melhor_opcao,
    CAST(NULL AS integer) as lead_time,
    
    -- Status e controles
    MIN(s.data_embarque) as data_embarque,
    MIN(s.numero_nf) as nf,
    MIN(s.status) as status,
    BOOL_OR(s.nf_cd) as nf_cd,
    MIN(s.pedido_cliente) as pedido_cliente,
    
    -- Controle de impressão
    BOOL_OR(s.separacao_impressa) as separacao_impressa,
    MIN(s.separacao_impressa_em) as separacao_impressa_em,
    MIN(s.separacao_impressa_por) as separacao_impressa_por,
    
    -- Relacionamentos
    MIN(s.cotacao_id) as cotacao_id,
    CAST(NULL AS integer) as usuario_id,
    
    -- Timestamps
    MIN(s.criado_em) as criado_em

FROM separacao s
WHERE s.separacao_lote_id IS NOT NULL
  AND s.status != 'PREVISAO'
GROUP BY s.separacao_lote_id;

-- 3. VERIFICAÇÃO
SELECT 'Total de pedidos na VIEW:' as info, COUNT(*) as total FROM pedidos
UNION ALL
SELECT 'Total de separações elegíveis:' as info, COUNT(DISTINCT separacao_lote_id) as total 
FROM separacao 
WHERE separacao_lote_id IS NOT NULL 
  AND status != 'PREVISAO';