#!/usr/bin/env python3
# TESTE SIMPLES - Execute no shell do Render
from app import create_app, db
app = create_app()

with app.app_context():
    # 1. VIEW existe?
    r = db.session.execute(db.text("SELECT COUNT(*) FROM information_schema.views WHERE table_name='pedidos'")).fetchone()
    print(f"VIEW existe? {r[0] > 0}")
    
    # 2. Quantas separações existem?
    r = db.session.execute(db.text("SELECT COUNT(*) FROM separacao")).fetchone()
    print(f"Total separações: {r[0]}")
    
    # 3. Quantas atendem critérios da VIEW?
    r = db.session.execute(db.text("SELECT COUNT(*) FROM separacao WHERE separacao_lote_id IS NOT NULL AND status != 'PREVISAO'")).fetchone()
    print(f"Separações válidas: {r[0]}")
    
    # 4. Quantos pedidos na VIEW?
    try:
        r = db.session.execute(db.text("SELECT COUNT(*) FROM pedidos")).fetchone()
        print(f"Pedidos na VIEW: {r[0]}")
    except Exception as e:
        print(f"ERRO ao acessar VIEW: {e}")
    
    # 5. Testar a conversão do ID problemático
    try:
        r = db.session.execute(db.text("SELECT ABS(('x' || substr(md5('TESTE123'), 1, 8))::bit(32)::int)")).fetchone()
        print(f"Conversão MD5 funciona: SIM - {r[0]}")
    except Exception as e:
        print(f"Conversão MD5 funciona: NÃO - {e}")