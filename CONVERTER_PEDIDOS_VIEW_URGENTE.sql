-- =====================================================
-- SCRIPT URGENTE PARA CONVERTER PEDIDOS EM VIEW
-- Data: 2025-01-30
-- 
-- ESTE SCRIPT RESOLVE TODOS OS PROBLEMAS DE UMA VEZ
-- =====================================================

-- 1. DROPAR VIEW DEPENDENTE (não funcional)
DROP VIEW IF EXISTS v_demanda_ativa CASCADE;

-- 2. DROPAR FOREIGN KEY DE cotacao_itens
ALTER TABLE cotacao_itens DROP CONSTRAINT IF EXISTS cotacao_itens_pedido_id_fkey;

-- 3. FAZER BACKUP DA TABELA ATUAL
ALTER TABLE pedidos RENAME TO pedidos_backup_30012025;

-- 4. CRIAR A VIEW PEDIDOS
CREATE VIEW pedidos AS
SELECT 
    -- ID usando ROW_NUMBER (mais compatível)
    ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id)::integer as id,
    
    -- Campos principais
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
    
    -- Campos de transporte (podem vir de JOIN depois)
    NULL::varchar(100) as transportadora,
    NULL::float as valor_frete,
    NULL::float as valor_por_kg,
    NULL::varchar(100) as nome_tabela,
    NULL::varchar(50) as modalidade,
    NULL::varchar(100) as melhor_opcao,
    NULL::float as valor_melhor_opcao,
    NULL::integer as lead_time,
    
    -- Status e controles
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
  AND s.status != 'PREVISAO'
GROUP BY s.separacao_lote_id;

-- 5. RECRIAR v_demanda_ativa CORRIGIDA (sem JOIN com pedido)
CREATE OR REPLACE VIEW v_demanda_ativa AS
SELECT 
    s.cod_produto,
    s.nome_produto,
    EXTRACT(MONTH FROM s.expedicao) as mes,
    EXTRACT(YEAR FROM s.expedicao) as ano,
    SUM(s.qtd_saldo) as qtd_demanda
FROM separacao s
WHERE s.status NOT IN ('FATURADO', 'PREVISAO')
  AND s.separacao_lote_id IS NOT NULL
GROUP BY s.cod_produto, s.nome_produto, mes, ano;

-- 6. VERIFICAÇÃO FINAL
SELECT 'VERIFICAÇÃO APÓS CONVERSÃO:' as info;
SELECT 'Total na VIEW pedidos:' as info, COUNT(*) as total FROM pedidos;
SELECT 'Total na tabela backup:' as info, COUNT(*) as total FROM pedidos_backup_30012025;
SELECT 'Total em v_demanda_ativa:' as info, COUNT(*) as total FROM v_demanda_ativa;

-- =====================================================
-- ROLLBACK (SE PRECISAR REVERTER):
-- DROP VIEW IF EXISTS pedidos CASCADE;
-- DROP VIEW IF EXISTS v_demanda_ativa CASCADE;
-- ALTER TABLE pedidos_backup_30012025 RENAME TO pedidos;
-- ALTER TABLE cotacao_itens ADD CONSTRAINT cotacao_itens_pedido_id_fkey 
--   FOREIGN KEY (pedido_id) REFERENCES pedidos(id);
-- =====================================================