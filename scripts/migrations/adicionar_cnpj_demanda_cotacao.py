"""
Migration: Adicionar origem_cnpj e destino_cnpj em carvia_sessao_demandas
=========================================================================
Campos opcionais para deteccao de grupo de cliente na cotacao.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        colunas = ['origem_cnpj', 'destino_cnpj']
        for col in colunas:
            existe = conn.execute(db.text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.columns "
                "  WHERE table_name = 'carvia_sessao_demandas' AND column_name = :col"
                ")"
            ), {'col': col}).scalar()
            print(f"  [BEFORE] {col}: {'EXISTE' if existe else 'NAO EXISTE'}")

            if not existe:
                conn.execute(db.text(
                    f"ALTER TABLE carvia_sessao_demandas "
                    f"ADD COLUMN {col} VARCHAR(20)"
                ))
                print(f"  [OK] {col} adicionado")

        conn.execute(db.text("COMMIT"))
        conn.close()

        # Verificacao
        conn2 = db.engine.connect()
        for col in colunas:
            existe = conn2.execute(db.text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.columns "
                "  WHERE table_name = 'carvia_sessao_demandas' AND column_name = :col"
                ")"
            ), {'col': col}).scalar()
            print(f"  [AFTER] {col}: {'EXISTE' if existe else 'FALHOU'}")
        conn2.close()

        print("\n=== Migration adicionar_cnpj_demanda_cotacao concluida ===")


if __name__ == '__main__':
    run()
