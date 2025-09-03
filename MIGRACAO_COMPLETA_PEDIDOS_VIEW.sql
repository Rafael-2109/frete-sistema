-- =====================================================
-- MIGRAÇÃO COMPLETA: PEDIDOS PARA VIEW
-- Data: 2025-01-30
-- 
-- ESTRATÉGIA:
-- 1. Migrar cotacao_itens para usar separacao_lote_id
-- 2. Converter pedidos em VIEW
-- 3. Usar separacao_lote_id como chave principal
-- =====================================================

-- PASSO 1: ADICIONAR COLUNA separacao_lote_id EM cotacao_itens
-- -------------------------------------------------------------
ALTER TABLE cotacao_itens 
ADD COLUMN IF NOT EXISTS separacao_lote_id VARCHAR(50);

-- PASSO 2: MIGRAR DADOS DE pedido_id PARA separacao_lote_id
-- -------------------------------------------------------------
UPDATE cotacao_itens ci
SET separacao_lote_id = p.separacao_lote_id
FROM pedidos p
WHERE ci.pedido_id = p.id
  AND ci.pedido_id IS NOT NULL;

-- Verificar migração
SELECT 'Registros migrados:' as info, 
       COUNT(*) as total 
FROM cotacao_itens 
WHERE separacao_lote_id IS NOT NULL;

-- PASSO 3: REMOVER CONSTRAINT E COLUNA ANTIGA
-- -------------------------------------------------------------
ALTER TABLE cotacao_itens 
DROP CONSTRAINT IF EXISTS cotacao_itens_pedido_id_fkey;

-- Manter pedido_id por enquanto (backup)
ALTER TABLE cotacao_itens 
RENAME COLUMN pedido_id TO pedido_id_old;

-- PASSO 4: FAZER BACKUP DA TABELA PEDIDOS
-- -------------------------------------------------------------
ALTER TABLE pedidos RENAME TO pedidos_tabela_backup;

-- PASSO 5: CRIAR VIEW PEDIDOS
-- -------------------------------------------------------------
CREATE VIEW pedidos AS
SELECT 
    -- ID extraído do separacao_lote_id (números após underscore)
    CASE 
        WHEN separacao_lote_id LIKE 'LOTE_%' THEN
            -- Extrai hash após LOTE_
            ('x' || substring(separacao_lote_id from 6 for 8))::bit(32)::int
        ELSE
            -- Usa hash do lote_id completo
            hashtext(separacao_lote_id)
    END as id,
    
    -- Identificador principal
    separacao_lote_id,
    
    -- Dados agregados
    MIN(s.num_pedido) as num_pedido,
    MIN(s.data_pedido) as data_pedido,
    MIN(s.cnpj_cpf) as cnpj_cpf,
    MIN(s.raz_social_red) as raz_social_red,
    MIN(s.nome_cidade) as nome_cidade,
    MIN(s.cod_uf) as cod_uf,
    MIN(s.cidade_normalizada) as cidade_normalizada,
    MIN(s.uf_normalizada) as uf_normalizada,
    MIN(s.codigo_ibge) as codigo_ibge,
    
    -- Valores
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
    
    -- Transporte
    NULL::varchar(100) as transportadora,
    NULL::float as valor_frete,
    NULL::float as valor_por_kg,
    NULL::varchar(100) as nome_tabela,
    NULL::varchar(50) as modalidade,
    NULL::varchar(100) as melhor_opcao,
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
  AND s.status != 'PREVISAO'
GROUP BY s.separacao_lote_id;

-- PASSO 6: RECRIAR v_demanda_ativa CORRIGIDA
-- -------------------------------------------------------------
DROP VIEW IF EXISTS v_demanda_ativa;

CREATE VIEW v_demanda_ativa AS
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

-- PASSO 7: CRIAR ÍNDICE EM cotacao_itens PARA PERFORMANCE
-- -------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_cotacao_itens_separacao_lote 
ON cotacao_itens(separacao_lote_id);

-- PASSO 8: VERIFICAÇÃO FINAL
-- -------------------------------------------------------------
SELECT 'VIEW pedidos criada com registros:' as info, COUNT(*) as total FROM pedidos;
SELECT 'cotacao_itens migrados:' as info, COUNT(*) as total FROM cotacao_itens WHERE separacao_lote_id IS NOT NULL;
SELECT 'v_demanda_ativa recriada:' as info, COUNT(*) as total FROM v_demanda_ativa;

-- =====================================================
-- ROLLBACK (SE NECESSÁRIO):
-- DROP VIEW IF EXISTS pedidos CASCADE;
-- DROP VIEW IF EXISTS v_demanda_ativa;
-- ALTER TABLE pedidos_tabela_backup RENAME TO pedidos;
-- ALTER TABLE cotacao_itens RENAME COLUMN pedido_id_old TO pedido_id;
-- ALTER TABLE cotacao_itens DROP COLUMN separacao_lote_id;
-- =====================================================