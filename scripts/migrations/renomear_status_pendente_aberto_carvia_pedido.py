"""
Migration: Renomear status PENDENTE -> ABERTO em carvia_pedidos
Alinha nomenclatura com Separacao Nacom (status ABERTO).

Executar: python scripts/migrations/renomear_status_pendente_aberto_carvia_pedido.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        # 1. Verificar estado ANTES
        result = db.session.execute(db.text(
            "SELECT status, COUNT(*) FROM carvia_pedidos GROUP BY status ORDER BY status"
        )).fetchall()
        print("ANTES:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        # 2. Atualizar dados: PENDENTE -> ABERTO
        updated = db.session.execute(db.text(
            "UPDATE carvia_pedidos SET status = 'ABERTO' WHERE status = 'PENDENTE'"
        )).rowcount
        print(f"\nAtualizado {updated} pedido(s) PENDENTE -> ABERTO")

        # 3. Recriar CHECK constraint
        db.session.execute(db.text(
            "ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status"
        ))
        db.session.execute(db.text(
            "ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status "
            "CHECK (status IN ('ABERTO','FATURADO','EMBARCADO','CANCELADO'))"
        ))
        print("CHECK constraint atualizada: PENDENTE -> ABERTO")

        # 4. Alterar DEFAULT
        db.session.execute(db.text(
            "ALTER TABLE carvia_pedidos ALTER COLUMN status SET DEFAULT 'ABERTO'"
        ))
        print("DEFAULT atualizado para 'ABERTO'")

        db.session.commit()

        # 5. Verificar estado DEPOIS
        result = db.session.execute(db.text(
            "SELECT status, COUNT(*) FROM carvia_pedidos GROUP BY status ORDER BY status"
        )).fetchall()
        print("\nDEPOIS:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")


if __name__ == '__main__':
    run()
