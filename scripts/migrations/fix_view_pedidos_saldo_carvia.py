"""
Migration: Fix VIEW pedidos — saldo CarVia cotacao (Part 2A)
Data: 2026-03-29
Descricao: Corrige Part 2A da VIEW pedidos para subtrair valores ja cobertos
           por pedidos com NF do valor_saldo_total e peso_total da cotacao.
           Antes: mostrava valor/peso cheio da cotacao.
           Depois: mostra saldo real (total - ja coberto por NF).

Executar: python scripts/migrations/fix_view_pedidos_saldo_carvia.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def executar():
    app = create_app()
    with app.app_context():
        # --- BEFORE ---
        print("=== BEFORE ===")
        antes = db.session.execute(
            db.text("""
                SELECT separacao_lote_id, num_pedido,
                       valor_saldo_total, peso_total
                FROM pedidos
                WHERE separacao_lote_id LIKE 'CARVIA-%'
                  AND separacao_lote_id NOT LIKE 'CARVIA-PED-%'
                ORDER BY separacao_lote_id
                LIMIT 10
            """)
        ).fetchall()
        if antes:
            for r in antes:
                print(f"  {r[0]}  num={r[1]}  valor={r[2]}  peso={r[3]}")
        else:
            print("  (nenhuma cotacao CarVia na VIEW)")

        # --- EXECUTAR SQL ---
        sql_path = os.path.join(
            os.path.dirname(__file__),
            'alterar_view_pedidos_union_carvia.sql',
        )
        with open(sql_path) as f:
            sql = f.read()

        print("\nExecutando DROP + CREATE VIEW...")
        db.session.execute(db.text(sql))
        db.session.commit()
        print("VIEW recriada.")

        # --- AFTER ---
        print("\n=== AFTER ===")
        depois = db.session.execute(
            db.text("""
                SELECT separacao_lote_id, num_pedido,
                       valor_saldo_total, peso_total
                FROM pedidos
                WHERE separacao_lote_id LIKE 'CARVIA-%'
                  AND separacao_lote_id NOT LIKE 'CARVIA-PED-%'
                ORDER BY separacao_lote_id
                LIMIT 10
            """)
        ).fetchall()
        if depois:
            for r in depois:
                print(f"  {r[0]}  num={r[1]}  valor={r[2]}  peso={r[3]}")
        else:
            print("  (nenhuma cotacao CarVia na VIEW)")

        # --- VERIFICACAO ---
        print("\n=== VERIFICACAO ===")
        negativos = db.session.execute(
            db.text("""
                SELECT COUNT(*)
                FROM pedidos
                WHERE separacao_lote_id LIKE 'CARVIA-%'
                  AND separacao_lote_id NOT LIKE 'CARVIA-PED-%'
                  AND (valor_saldo_total < 0 OR peso_total < 0)
            """)
        ).scalar()
        if negativos == 0:
            print("  OK: nenhum saldo negativo encontrado.")
        else:
            print(f"  ALERTA: {negativos} linhas com saldo negativo!")

        print("\nMigration concluida.")


if __name__ == '__main__':
    executar()
