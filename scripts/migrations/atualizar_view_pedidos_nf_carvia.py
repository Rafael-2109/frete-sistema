"""
Migration: Atualizar VIEW pedidos — NF para CarVia Part 2B
Data: 2026-03-25
Descricao: Re-cria a VIEW pedidos com subquery de NF na Part 2B.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def executar():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(
            os.path.dirname(__file__),
            'alterar_view_pedidos_union_carvia.sql',
        )
        with open(sql_path) as f:
            sql = f.read()

        print("Verificando VIEW atual...")
        resultado_antes = db.session.execute(
            db.text("""
                SELECT nf FROM pedidos
                WHERE separacao_lote_id LIKE 'CARVIA-PED-%'
                LIMIT 5
            """)
        ).fetchall()
        print(f"  NFs antes: {[r[0] for r in resultado_antes]}")

        print("Executando DROP + CREATE VIEW...")
        db.session.execute(db.text(sql))
        db.session.commit()

        resultado_depois = db.session.execute(
            db.text("""
                SELECT separacao_lote_id, num_pedido, nf
                FROM pedidos
                WHERE separacao_lote_id LIKE 'CARVIA-PED-%'
                LIMIT 5
            """)
        ).fetchall()
        print("NFs depois:")
        for r in resultado_depois:
            print(f"  {r[0]} {r[1]} nf={r[2]}")

        print("VIEW atualizada com sucesso.")


if __name__ == '__main__':
    executar()
