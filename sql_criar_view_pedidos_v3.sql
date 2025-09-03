-- =====================================================
-- CRIAR VIEW PEDIDOS PARA SUBSTITUIR TABELA (V3)
-- Data: 2025-01-29
-- Versão corrigida: apenas campos que existem em Pedido
-- =====================================================

-- 1. RENOMEAR TABELA ORIGINAL (BACKUP)
-- =====================================================
-- ALTER TABLE pedidos RENAME TO pedidos_backup;

-- 2. CRIAR VIEW PEDIDOS AGREGANDO SEPARACAO
-- =====================================================
CREATE OR REPLACE VIEW pedidos AS
SELECT 
    -- ID virtual baseado no lote + num_pedido
    ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id, s.num_pedido) as id,
    
    -- Identificadores principais
    s.separacao_lote_id,
    s.num_pedido,
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
    
    -- Campos de transporte (NULL - virão de JOIN com cotacao quando necessário)
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
    
    -- Controle de impressão
    BOOL_OR(s.separacao_impressa) as separacao_impressa,
    MIN(s.separacao_impressa_em) as separacao_impressa_em,
    MIN(s.separacao_impressa_por) as separacao_impressa_por,
    
    -- Relacionamentos (NULL por enquanto)
    NULL::integer as cotacao_id,
    NULL::integer as usuario_id,
    
    -- Timestamps
    MIN(s.criado_em) as criado_em

FROM separacao s
WHERE s.separacao_lote_id IS NOT NULL
  AND s.status != 'PREVISAO'  -- Excluir pré-separações da VIEW
GROUP BY s.separacao_lote_id, s.num_pedido;

-- 3. CRIAR REGRAS (RULES) PARA UPDATE NA VIEW
-- =====================================================

-- 3.1 RULE para UPDATE de status
CREATE OR REPLACE RULE pedidos_update_status AS
ON UPDATE TO pedidos
WHERE NEW.status IS DISTINCT FROM OLD.status
DO INSTEAD
UPDATE separacao
SET status = NEW.status
WHERE separacao_lote_id = NEW.separacao_lote_id
  AND num_pedido = NEW.num_pedido;

-- 3.2 RULE para UPDATE de nf_cd
CREATE OR REPLACE RULE pedidos_update_nf_cd AS
ON UPDATE TO pedidos
WHERE NEW.nf_cd IS DISTINCT FROM OLD.nf_cd
DO INSTEAD
UPDATE separacao
SET nf_cd = NEW.nf_cd
WHERE separacao_lote_id = NEW.separacao_lote_id
  AND num_pedido = NEW.num_pedido;

-- 3.3 RULE para UPDATE de data_embarque
CREATE OR REPLACE RULE pedidos_update_embarque AS
ON UPDATE TO pedidos
WHERE NEW.data_embarque IS DISTINCT FROM OLD.data_embarque
DO INSTEAD
UPDATE separacao
SET data_embarque = NEW.data_embarque
WHERE separacao_lote_id = NEW.separacao_lote_id
  AND num_pedido = NEW.num_pedido;

-- 3.4 RULE para UPDATE de agendamento
CREATE OR REPLACE RULE pedidos_update_agendamento AS
ON UPDATE TO pedidos
WHERE (NEW.agendamento IS DISTINCT FROM OLD.agendamento 
    OR NEW.protocolo IS DISTINCT FROM OLD.protocolo
    OR NEW.agendamento_confirmado IS DISTINCT FROM OLD.agendamento_confirmado)
DO INSTEAD
UPDATE separacao
SET 
    agendamento = NEW.agendamento,
    protocolo = NEW.protocolo,
    agendamento_confirmado = NEW.agendamento_confirmado
WHERE separacao_lote_id = NEW.separacao_lote_id
  AND num_pedido = NEW.num_pedido;

-- 3.5 RULE para UPDATE de impressão
CREATE OR REPLACE RULE pedidos_update_impressao AS
ON UPDATE TO pedidos
WHERE (NEW.separacao_impressa IS DISTINCT FROM OLD.separacao_impressa
    OR NEW.separacao_impressa_em IS DISTINCT FROM OLD.separacao_impressa_em
    OR NEW.separacao_impressa_por IS DISTINCT FROM OLD.separacao_impressa_por)
DO INSTEAD
UPDATE separacao
SET 
    separacao_impressa = NEW.separacao_impressa,
    separacao_impressa_em = NEW.separacao_impressa_em,
    separacao_impressa_por = NEW.separacao_impressa_por
WHERE separacao_lote_id = NEW.separacao_lote_id
  AND num_pedido = NEW.num_pedido;

-- 4. VERIFICAÇÃO
-- =====================================================

-- Comparar totais com tabela original
SELECT 
    'pedidos_backup (original)' as fonte,
    COUNT(*) as total
FROM pedidos_backup
UNION ALL
SELECT 
    'pedidos (VIEW)' as fonte,
    COUNT(*) as total
FROM pedidos;

-- Testar agregações
SELECT 
    separacao_lote_id,
    num_pedido,
    status,
    nf_cd,
    valor_saldo_total,
    peso_total,
    pallet_total
FROM pedidos
LIMIT 5;