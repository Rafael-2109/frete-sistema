"""
GAP-01: Converter status EMITIDA → PENDENTE em carvia_faturas_cliente.

O status EMITIDA nunca era setado automaticamente pelo fluxo.
Qualquer registro existente com EMITIDA deve ser convertido para PENDENTE.

Idempotente: roda quantas vezes quiser sem efeito colateral.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        # Verificar antes
        result = db.session.execute(
            db.text(
                "SELECT COUNT(*) FROM carvia_faturas_cliente WHERE status = 'EMITIDA'"
            )
        )
        count_before = result.scalar()
        print(f"[ANTES] Faturas com status EMITIDA: {count_before}")

        if count_before == 0:
            print("Nenhuma fatura com status EMITIDA. Nada a fazer.")
            return

        # Converter
        db.session.execute(
            db.text(
                "UPDATE carvia_faturas_cliente SET status = 'PENDENTE' WHERE status = 'EMITIDA'"
            )
        )
        db.session.commit()

        # Verificar depois
        result = db.session.execute(
            db.text(
                "SELECT COUNT(*) FROM carvia_faturas_cliente WHERE status = 'EMITIDA'"
            )
        )
        count_after = result.scalar()
        print(f"[DEPOIS] Faturas com status EMITIDA: {count_after}")
        print(f"Convertidas: {(count_before or 0) - (count_after or 0)}")


if __name__ == '__main__':
    run()
