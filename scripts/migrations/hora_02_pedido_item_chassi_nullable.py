"""Migration HORA 02: hora_pedido_item.numero_chassi nullable.

Permite pedido pre-NF (cliente solicita motos sem chassis atribuidos).
Unica excecao ao invariante 2.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def is_nullable():
    result = db.session.execute(
        db.text(
            """
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name = 'hora_pedido_item' AND column_name = 'numero_chassi'
            """
        )
    ).scalar()
    return result == 'YES'


def has_partial_unique_index():
    result = db.session.execute(
        db.text(
            """
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'hora_pedido_item'
              AND indexname = 'uq_hora_pedido_item_chassi_parcial'
            """
        )
    ).scalar()
    return result is not None


def verificar_antes():
    print(f"[BEFORE] numero_chassi nullable: {'SIM' if is_nullable() else 'NAO'}")
    print(f"[BEFORE] index parcial existe: {'SIM' if has_partial_unique_index() else 'NAO'}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_02_pedido_item_chassi_nullable.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    assert is_nullable(), "numero_chassi ainda NOT NULL"
    assert has_partial_unique_index(), "index parcial nao foi criado"
    print(f"[AFTER] numero_chassi nullable: SIM")
    print(f"[AFTER] index parcial uq_hora_pedido_item_chassi_parcial: SIM")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 02 concluida")
