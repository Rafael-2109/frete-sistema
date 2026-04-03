"""
Migration: Adicionar modelo_moto_id em carvia_nf_itens
=====================================================

Persiste o modelo de moto detectado na importacao.
Editavel manualmente pelo usuario como fallback.

Uso: python scripts/migrations/add_modelo_moto_id_nf_itens.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db  # noqa: E402


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_nf_itens' AND column_name = 'modelo_moto_id'
    """))
    existe = result.fetchone() is not None
    print(f"[BEFORE] Coluna modelo_moto_id existe: {existe}")
    return existe


def executar():
    """Adiciona coluna modelo_moto_id + indice."""
    db.session.execute(db.text("""
        ALTER TABLE carvia_nf_itens
            ADD COLUMN modelo_moto_id INTEGER
            REFERENCES carvia_modelos_moto(id)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_nf_itens_modelo_moto_id
            ON carvia_nf_itens(modelo_moto_id)
    """))
    db.session.commit()
    print("[OK] Coluna modelo_moto_id adicionada com indice")


def verificar_depois():
    """Verifica estado apos migration."""
    result = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_nf_itens' AND column_name = 'modelo_moto_id'
    """))
    existe = result.fetchone() is not None
    print(f"[AFTER] Coluna modelo_moto_id existe: {existe}")

    result = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_nf_itens' AND indexname = 'ix_carvia_nf_itens_modelo_moto_id'
    """))
    idx = result.fetchone() is not None
    print(f"[AFTER] Indice ix_carvia_nf_itens_modelo_moto_id existe: {idx}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        ja_existe = verificar_antes()
        if ja_existe:
            print("[SKIP] Coluna ja existe — nada a fazer")
        else:
            executar()
        verificar_depois()
