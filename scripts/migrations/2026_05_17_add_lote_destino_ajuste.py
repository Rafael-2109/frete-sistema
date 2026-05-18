"""D004/D005: adiciona lote_destino + lote_origem em ajuste_estoque_inventario."""
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        # before
        existing = db.session.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='ajuste_estoque_inventario'
              AND column_name IN ('lote_destino', 'lote_origem')
        """)).fetchall()
        print(f"Antes: {[r[0] for r in existing]}")

        db.session.execute(db.text(
            "ALTER TABLE ajuste_estoque_inventario "
            "ADD COLUMN IF NOT EXISTS lote_destino VARCHAR(60)"
        ))
        db.session.execute(db.text(
            "ALTER TABLE ajuste_estoque_inventario "
            "ADD COLUMN IF NOT EXISTS lote_origem VARCHAR(60)"
        ))
        db.session.commit()

        existing = db.session.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='ajuste_estoque_inventario'
              AND column_name IN ('lote_destino', 'lote_origem')
        """)).fetchall()
        print(f"Depois: {[r[0] for r in existing]}")


if __name__ == '__main__':
    main()
