-- =====================================================
-- CRIAR VIEW PEDIDOS FINAL COM ID DETERMINÍSTICO
-- Data: 2025-01-29
-- 
-- IMPORTANTE: separacao_lote_id é único por pedido
-- Usa hash MD5 para gerar ID consistente
-- =====================================================

-- 1. RENOMEAR TABELA ORIGINAL (BACKUP) - só executar uma vez
-- ALTER TABLE pedidos RENAME TO pedidos_backup;

-- 2. CRIAR VIEW PEDIDOS COM ID DETERMINÍSTICO
-- =====================================================
DROP VIEW IF EXISTS pedidos CASCADE;

CREATE VIEW pedidos AS
SELECT 
    -- ID determinístico baseado em hash do separacao_lote_id
    -- Usa ABS para garantir número positivo e MOD para limitar tamanho
    ABS(('x' || substr(md5(s.separacao_lote_id), 1, 8))::bit(32)::int) as id,
    
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
    MIN(s.numero_nf) as nf,  -- Mapeia numero_nf para nf
    MIN(s.status) as status,
    BOOL_OR(s.nf_cd) as nf_cd,
    MIN(s.pedido_cliente) as pedido_cliente,
    
    -- Controle de impressão
    BOOL_OR(s.separacao_impressa) as separacao_impressa,
    MIN(s.separacao_impressa_em) as separacao_impressa_em,
    MIN(s.separacao_impressa_por) as separacao_impressa_por,
    
    -- Relacionamentos
    MIN(s.cotacao_id) as cotacao_id,
    NULL::integer as usuario_id,
    
    -- Timestamps
    MIN(s.criado_em) as criado_em

FROM separacao s
WHERE s.separacao_lote_id IS NOT NULL
  AND s.status != 'PREVISAO'  -- EXCLUIR REGISTROS COM STATUS PREVISAO
GROUP BY s.separacao_lote_id;

-- 3. CRIAR TODAS AS REGRAS (RULES) PARA UPDATE NA VIEW
-- =====================================================

-- 3.1 RULE para UPDATE de status
CREATE OR REPLACE RULE pedidos_update_status AS
ON UPDATE TO pedidos
WHERE NEW.status IS DISTINCT FROM OLD.status
DO INSTEAD
UPDATE separacao
SET status = NEW.status
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.2 RULE para UPDATE de nf_cd
CREATE OR REPLACE RULE pedidos_update_nf_cd AS
ON UPDATE TO pedidos
WHERE NEW.nf_cd IS DISTINCT FROM OLD.nf_cd
DO INSTEAD
UPDATE separacao
SET nf_cd = NEW.nf_cd
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.3 RULE para UPDATE de data_embarque
CREATE OR REPLACE RULE pedidos_update_embarque AS
ON UPDATE TO pedidos
WHERE NEW.data_embarque IS DISTINCT FROM OLD.data_embarque
DO INSTEAD
UPDATE separacao
SET data_embarque = NEW.data_embarque
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.4 RULE para UPDATE de agendamento (múltiplos campos)
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
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.5 RULE para UPDATE de nf (mapeia para numero_nf)
CREATE OR REPLACE RULE pedidos_update_nf AS
ON UPDATE TO pedidos
WHERE NEW.nf IS DISTINCT FROM OLD.nf
DO INSTEAD
UPDATE separacao
SET numero_nf = NEW.nf
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.6 RULE para UPDATE de impressão
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
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.7 RULE para UPDATE de normalização de cidade
CREATE OR REPLACE RULE pedidos_update_normalizacao AS
ON UPDATE TO pedidos
WHERE (NEW.cidade_normalizada IS DISTINCT FROM OLD.cidade_normalizada
    OR NEW.uf_normalizada IS DISTINCT FROM OLD.uf_normalizada
    OR NEW.codigo_ibge IS DISTINCT FROM OLD.codigo_ibge)
DO INSTEAD
UPDATE separacao
SET 
    cidade_normalizada = NEW.cidade_normalizada,
    uf_normalizada = NEW.uf_normalizada,
    codigo_ibge = NEW.codigo_ibge
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.8 RULE para UPDATE de rota
CREATE OR REPLACE RULE pedidos_update_rota AS
ON UPDATE TO pedidos
WHERE (NEW.rota IS DISTINCT FROM OLD.rota
    OR NEW.sub_rota IS DISTINCT FROM OLD.sub_rota
    OR NEW.roteirizacao IS DISTINCT FROM OLD.roteirizacao)
DO INSTEAD
UPDATE separacao
SET 
    rota = NEW.rota,
    sub_rota = NEW.sub_rota,
    roteirizacao = NEW.roteirizacao
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.9 RULE para UPDATE de expedicao
CREATE OR REPLACE RULE pedidos_update_expedicao AS
ON UPDATE TO pedidos
WHERE NEW.expedicao IS DISTINCT FROM OLD.expedicao
DO INSTEAD
UPDATE separacao
SET expedicao = NEW.expedicao
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.10 RULE para UPDATE de observações
CREATE OR REPLACE RULE pedidos_update_observacoes AS
ON UPDATE TO pedidos
WHERE NEW.observ_ped_1 IS DISTINCT FROM OLD.observ_ped_1
DO INSTEAD
UPDATE separacao
SET observ_ped_1 = NEW.observ_ped_1
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.11 RULE para UPDATE de pedido_cliente
CREATE OR REPLACE RULE pedidos_update_pedido_cliente AS
ON UPDATE TO pedidos
WHERE NEW.pedido_cliente IS DISTINCT FROM OLD.pedido_cliente
DO INSTEAD
UPDATE separacao
SET pedido_cliente = NEW.pedido_cliente
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.12 RULE para UPDATE de cotacao_id
CREATE OR REPLACE RULE pedidos_update_cotacao AS
ON UPDATE TO pedidos
WHERE NEW.cotacao_id IS DISTINCT FROM OLD.cotacao_id
DO INSTEAD
UPDATE separacao
SET cotacao_id = NEW.cotacao_id
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3.13 RULE para UPDATE de data_pedido (raramente muda)
CREATE OR REPLACE RULE pedidos_update_data_pedido AS
ON UPDATE TO pedidos
WHERE NEW.data_pedido IS DISTINCT FROM OLD.data_pedido
DO INSTEAD
UPDATE separacao
SET data_pedido = NEW.data_pedido
WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 4. RULE para DELETE - NÃO marca como sincronizado
-- =====================================================
CREATE OR REPLACE RULE pedidos_delete AS
ON DELETE TO pedidos
DO INSTEAD
DELETE FROM separacao
WHERE separacao_lote_id = OLD.separacao_lote_id;

-- 5. RULE para INSERT - Bloquear (pedidos só criados via Separacao)
-- =====================================================
CREATE OR REPLACE RULE pedidos_insert AS
ON INSERT TO pedidos
DO INSTEAD NOTHING;

-- 6. CRIAR FUNÇÃO PARA MAPEAR ID PARA LOTE (útil para debug)
-- =====================================================
CREATE OR REPLACE FUNCTION pedido_id_para_lote(pedido_id INTEGER)
RETURNS VARCHAR(50) AS $$
BEGIN
    RETURN (
        SELECT separacao_lote_id 
        FROM pedidos 
        WHERE id = pedido_id
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- 7. CRIAR ÍNDICE PARA BUSCA POR ID (performance)
-- =====================================================
-- Como ID é calculado, criar índice funcional em Separacao
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_lote_hash 
ON separacao (ABS(('x' || substr(md5(separacao_lote_id), 1, 8))::bit(32)::int))
WHERE separacao_lote_id IS NOT NULL;

-- 8. VERIFICAÇÃO
-- =====================================================

-- Testar IDs gerados
SELECT 
    id,
    separacao_lote_id,
    num_pedido,
    status
FROM pedidos
LIMIT 10;

-- Verificar que IDs são únicos
SELECT 
    COUNT(*) as total_pedidos,
    COUNT(DISTINCT id) as ids_unicos,
    COUNT(DISTINCT separacao_lote_id) as lotes_unicos
FROM pedidos;

-- Testar busca por ID
EXPLAIN ANALYZE
SELECT * FROM pedidos WHERE id = 123456;



python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    # 1. Fazer backup da tabela atual
    try:
        db.session.execute(db.text('ALTER TABLE pedidos RENAME TO pedidos_backup_old'))
        db.session.commit()
        print('1. Backup criado: pedidos_backup_old')
    except Exception as e:
        print(f'1. Erro no backup (talvez já exista): {e}')
        db.session.rollback()    
    # 2. Criar a VIEW
    sql = '''
    CREATE VIEW pedidos AS
    SELECT 
        ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id)::integer as id,
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
    GROUP BY s.separacao_lote_id
    '''
    try:
        db.session.execute(db.text(sql))
        db.session.commit()
        print('2. VIEW criada com sucesso!')
    except Exception as e:
        print(f'2. Erro ao criar VIEW: {e}')
        db.session.rollback()
    
    # 3. Verificar resultado
    count = db.session.execute(db.text('SELECT COUNT(*) FROM pedidos')).fetchone()[0]
    print(f'3. Total na nova VIEW: {count} (esperado: ~2416)')
"



python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    # 1. Verificar se há triggers/constraints na tabela
    r = db.session.execute(db.text(\"\"\"
        SELECT COUNT(*) FROM information_schema.table_constraints 
        WHERE table_name = 'pedidos' AND constraint_type != 'CHECK'
    \"\"\")).fetchone()
    print(f'1. Constraints em pedidos: {r[0]}')     
    # 2. Verificar índices
    r = db.session.execute(db.text(\"\"\"
        SELECT COUNT(*) FROM pg_indexes 
        WHERE tablename = 'pedidos'
    \"\"\")).fetchone()
    print(f'2. Índices em pedidos: {r[0]}')     
    # 3. Ver os 62 registros de diferença
    r = db.session.execute(db.text(\"\"\"
        SELECT COUNT(*) FROM pedidos p
        WHERE NOT EXISTS (
            SELECT 1 FROM separacao s
            WHERE s.separacao_lote_id = p.separacao_lote_id
            AND s.status != 'PREVISAO'
        )
    \"\"\")).fetchone()
    print(f'3. Pedidos que não existem mais em separacao: {r[0]}')    
    # 4. Verificar dependências
    r = db.session.execute(db.text(\"\"\"
        SELECT COUNT(*) FROM information_schema.view_table_usage
        WHERE table_name = 'pedidos'
    \"\"\")).fetchone()
    print(f'4. Views que dependem de pedidos: {r[0]}')
"


python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    # 1. Quais são as constraints?
    r = db.session.execute(db.text(\"\"\"
        SELECT constraint_name, constraint_type 
        FROM information_schema.table_constraints 
        WHERE table_name = 'pedidos'
    \"\"\")).fetchall()
    print('1. CONSTRAINTS:')
    for c in r:
        print(f'   - {c[0]}: {c[1]}')
    
    # 2. Quais são os índices?
    r = db.session.execute(db.text(\"\"\"
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'pedidos'
    \"\"\")).fetchall()
    print('2. ÍNDICES:')
    for i in r:
        print(f'   - {i[0]}')
    
    # 3. Qual VIEW depende de pedidos?
    r = db.session.execute(db.text(\"\"\"
        SELECT view_schema, view_name 
        FROM information_schema.view_table_usage
        WHERE table_name = 'pedidos'
    \"\"\")).fetchall()
    print('3. VIEWS DEPENDENTES:')
    for v in r:
        print(f'   - {v[0]}.{v[1]}')
    
    # 4. Há foreign keys apontando para pedidos?
    r = db.session.execute(db.text(\"\"\"
        SELECT tc.table_name, tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.referential_constraints rc
        ON tc.constraint_name = rc.constraint_name
        WHERE rc.unique_constraint_name IN (
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'pedidos'
        )
    \"\"\")).fetchall()
    print('4. TABELAS QUE REFERENCIAM PEDIDOS:')
    for t in r:
        print(f'   - {t[0]} ({t[1]})')
"


python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    print('VERIFICANDO IMPACTOS DA CONVERSÃO:')
    print('='*50)
    # 1. Verificar se cotacao_itens tem registros
    r = db.session.execute(db.text('SELECT COUNT(*) FROM cotacao_itens WHERE pedido_id IS NOT NULL')).fetchone()
    if r and r[0] > 0:
        print(f'❌ PROBLEMA: {r[0]} registros em cotacao_itens referenciam pedidos')
        print('   Esses registros perderão a referência!')
    else:
        print('✅ cotacao_itens: Sem registros usando pedido_id')
    # 2. Verificar código que usa pedidos.id
    r = db.session.execute(db.text(\"\"\"
        SELECT DISTINCT separacao_lote_id, num_pedido
        FROM pedidos
        WHERE id IN (
            SELECT pedido_id FROM cotacao_itens WHERE pedido_id IS NOT NULL ) LIMIT 5
    \"\"\")).fetchall()
    if r:
        print('   Pedidos afetados:')
        for p in r:
            print(f'     - Lote: {p[0]}, Pedido: {p[1]}')
    # 3. Verificar se alguma VIEW usa pedidos.id
    print('')
    print('RECOMENDAÇÃO:')
    if r and r[0] > 0:
        print('⚠️  Fazer backup de cotacao_itens antes!')
        print('⚠️  Considerar migrar pedido_id para separacao_lote_id')
    else:
        print('✅ Parece seguro prosseguir com a conversão')
"