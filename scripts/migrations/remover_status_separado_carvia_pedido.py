"""
Migration: Remover status SEPARADO de carvia_pedidos
Data: 22/03/2026
"""

from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        # Verificar antes
        result = db.session.execute(
            text("SELECT COUNT(*) FROM carvia_pedidos WHERE status = 'SEPARADO'")
        ).scalar()
        print(f"Pedidos com status SEPARADO: {result}")

        if result > 0:
            db.session.execute(
                text("UPDATE carvia_pedidos SET status = 'PENDENTE' WHERE status = 'SEPARADO'")
            )
            print(f"  → {result} pedido(s) atualizados para PENDENTE")

        # Recriar constraint
        db.session.execute(text(
            "ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status"
        ))
        db.session.execute(text(
            "ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status "
            "CHECK (status IN ('PENDENTE', 'FATURADO', 'EMBARCADO', 'CANCELADO'))"
        ))
        print("CheckConstraint atualizada (sem SEPARADO)")

        db.session.commit()
        print("Migration concluida com sucesso.")


if __name__ == '__main__':
    main()
