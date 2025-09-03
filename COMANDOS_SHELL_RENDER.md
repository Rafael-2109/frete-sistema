# COMANDOS PARA EXECUTAR NO SHELL DO RENDER

## 1. Entrar no Python e testar a VIEW:
```python
python3
from app import create_app, db
app = create_app()
app.app_context().push()

# Teste 1: VIEW existe?
db.session.execute(db.text("SELECT COUNT(*) FROM information_schema.views WHERE table_name='pedidos'")).fetchone()

# Teste 2: Quantos registros na VIEW?
db.session.execute(db.text("SELECT COUNT(*) FROM pedidos")).fetchone()

# Teste 3: Erro na conversão MD5?
db.session.execute(db.text("SELECT ABS(('x' || substr(md5('TEST'), 1, 8))::bit(32)::int)")).fetchone()
```

## 2. Se der erro na conversão MD5, recriar VIEW simples:
```python
# Dropar VIEW antiga
db.session.execute(db.text("DROP VIEW IF EXISTS pedidos CASCADE"))
db.session.commit()

# Criar VIEW simples com ROW_NUMBER
sql = """
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
"""
db.session.execute(db.text(sql))
db.session.commit()

# Verificar se funcionou
db.session.execute(db.text("SELECT COUNT(*) FROM pedidos")).fetchone()
```

## 3. Teste rápido - copiar e colar tudo:
```bash
python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    print('1. VIEW existe?', db.session.execute(db.text(\"SELECT EXISTS(SELECT 1 FROM information_schema.views WHERE table_name='pedidos')\")).fetchone()[0])
    try:
        count = db.session.execute(db.text('SELECT COUNT(*) FROM pedidos')).fetchone()[0]
        print(f'2. Pedidos na VIEW: {count}')
    except Exception as e:
        print(f'2. ERRO na VIEW: {e}')
    try:
        db.session.execute(db.text(\"SELECT ABS(('x' || substr(md5('TEST'), 1, 8))::bit(32)::int)\")).fetchone()
        print('3. Conversão MD5: OK')
    except:
        print('3. Conversão MD5: ERRO - Esse é o problema!')
"
```