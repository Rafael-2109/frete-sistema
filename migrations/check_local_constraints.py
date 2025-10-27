"""
Verifica constraints e índices no banco LOCAL
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def check_local_database():
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("VERIFICANDO BANCO LOCAL - grupo_empresarial")
        print("=" * 70)

        # Constraints
        print("\nCONSTRAINTS:")
        result = db.session.execute(text("""
            SELECT conname, pg_get_constraintdef(oid) as definicao
            FROM pg_constraint
            WHERE conrelid = 'grupo_empresarial'::regclass
            ORDER BY conname
        """))

        for c in result.fetchall():
            print(f"  - {c[0]}: {c[1]}")

        # Índices
        print("\nÍNDICES:")
        result = db.session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'grupo_empresarial'
            ORDER BY indexname
        """))

        for idx in result.fetchall():
            unique = "UNIQUE" in idx[1]
            print(f"  - {idx[0]} {'[UNIQUE]' if unique else ''}")
            print(f"    {idx[1]}")

if __name__ == '__main__':
    check_local_database()
