"""
Migration: Renomear status FATURADO -> COTADO em carvia_pedidos
================================================================

Fluxo final: ABERTO -> COTADO -> EMBARCADO (sem FATURADO)
COTADO = pedido em embarque (ha cotacao de compra associada)

Executar: python scripts/migrations/renomear_status_faturado_cotado_carvia_pedidos.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def migrar():
    app = create_app()
    with app.app_context():
        # 1. Estado ANTES
        result = db.session.execute(text(
            "SELECT status, COUNT(*) FROM carvia_pedidos GROUP BY status ORDER BY status"
        ))
        print("Estado ANTES:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        # 2. Verificar se migration ja foi executada
        faturados = db.session.execute(text(
            "SELECT COUNT(*) FROM carvia_pedidos WHERE status = 'FATURADO'"
        )).scalar() or 0

        if faturados == 0:
            # Verificar se constraint ja foi atualizada
            constraint_check = db.session.execute(text("""
                SELECT conname, consrc FROM pg_constraint
                WHERE conname = 'ck_carvia_pedido_status'
            """)).first()
            if constraint_check and 'COTADO' in str(constraint_check[1]):
                print("\nMigration ja foi executada anteriormente.")
                return

        # 3. Converter FATURADO -> ABERTO (status_calculado recalcula dinamicamente)
        if faturados > 0:
            print(f"\nConvertendo {faturados} pedido(s) FATURADO -> ABERTO...")
            db.session.execute(text(
                "UPDATE carvia_pedidos SET status = 'ABERTO' WHERE status = 'FATURADO'"
            ))

        # 4. Recriar CHECK constraint
        print("Recriando CHECK constraint...")
        db.session.execute(text(
            "ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status"
        ))
        db.session.execute(text("""
            ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status
            CHECK (status IN ('ABERTO','COTADO','EMBARCADO','CANCELADO'))
        """))

        db.session.commit()

        # 5. Estado DEPOIS
        result = db.session.execute(text(
            "SELECT status, COUNT(*) FROM carvia_pedidos GROUP BY status ORDER BY status"
        ))
        print("\nEstado DEPOIS:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

        print("\nMigration concluida com sucesso!")


if __name__ == '__main__':
    migrar()
