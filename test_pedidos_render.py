python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    # 1. É uma tabela ou view?
    r = db.session.execute(db.text(\"SELECT table_type FROM information_schema.tables WHERE table_name='pedidos'\")).fetchone()
    if r:
        print(f'1. pedidos é: {r[0]}')
    else:
        print('1. pedidos não encontrado em information_schema.tables')
    
    # 2. Verificar em todos os schemas
    r = db.session.execute(db.text(\"SELECT table_schema, table_type FROM information_schema.tables WHERE table_name='pedidos'\")).fetchall()
    for schema in r:
        print(f'   - Schema: {schema[0]}, Tipo: {schema[1]}')
    
    # 3. Quantos registros?
    try:
        count = db.session.execute(db.text('SELECT COUNT(*) FROM pedidos')).fetchone()[0]
        print(f'2. Total em pedidos: {count}')
    except Exception as e:
        print(f'2. Erro: {e}')
    
    # 4. Verificar separações válidas
    count = db.session.execute(db.text(\"SELECT COUNT(DISTINCT separacao_lote_id) FROM separacao WHERE separacao_lote_id IS NOT NULL AND status != 'PREVISAO'\")).fetchone()[0]
    print(f'3. Separações que deveriam aparecer: {count}')
    
    # 5. Ver estrutura de pedidos
    cols = db.session.execute(db.text(\"SELECT column_name FROM information_schema.columns WHERE table_name='pedidos' LIMIT 5\")).fetchall()
    if cols:
        print('4. Primeiras colunas de pedidos:', [c[0] for c in cols])
"