"""Adicionar peso_cubado ao embarque_itens."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db

app = create_app()
with app.app_context():
    sql_path = os.path.join(os.path.dirname(__file__), 'add_peso_cubado_embarque_item.sql')
    with open(sql_path) as f:
        sql = f.read()

    print("[ANTES]")
    exists = db.session.execute(db.text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'embarque_itens' AND column_name = 'peso_cubado'
    """)).scalar()
    print(f"  peso_cubado exists: {bool(exists)}")

    db.session.execute(db.text(sql))
    db.session.commit()

    print("[DEPOIS]")
    exists = db.session.execute(db.text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'embarque_itens' AND column_name = 'peso_cubado'
    """)).scalar()
    print(f"  peso_cubado exists: {bool(exists)}")
    print("Migration concluida.")
