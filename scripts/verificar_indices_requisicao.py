import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Verificar ÍNDICES
    print("\n📊 ÍNDICES na tabela requisicao_compras:")
    resultado = db.session.execute(text("""
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = 'requisicao_compras'
        ORDER BY indexname;
    """))
    
    indices = resultado.fetchall()
    for idx in indices:
        print(f"   - {idx[0]}")
        print(f"     {idx[1]}\n")
    
    # Verificar CONSTRAINTS
    print("\n📋 CONSTRAINTS UNIQUE:")
    resultado = db.session.execute(text("""
        SELECT
            conname as constraint_name,
            pg_get_constraintdef(oid) as definition
        FROM pg_constraint
        WHERE conrelid = 'requisicao_compras'::regclass
        AND contype = 'u'
        ORDER BY conname;
    """))
    
    constraints = resultado.fetchall()
    for con in constraints:
        print(f"   - {con[0]}: {con[1]}")
