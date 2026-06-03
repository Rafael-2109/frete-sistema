"""Migration hora_43: NF entrada item — flag desconsiderado + relaxar FK numero_chassi.

Spec: docs/superpowers/specs/2026-06-03-hora-desconsiderar-moto-nf-design.md
Idempotente. Rodar da raiz: python scripts/migrations/hora_43_nf_item_desconsiderar.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

SQL_COLUNA = (
    "ALTER TABLE hora_nf_entrada_item "
    "ADD COLUMN IF NOT EXISTS desconsiderado BOOLEAN NOT NULL DEFAULT false"
)
SQL_INDEX = (
    "CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_item_desconsiderado "
    "ON hora_nf_entrada_item (desconsiderado)"
)
SQL_DROP_FK = """
DO $$
DECLARE cname text;
BEGIN
    SELECT conname INTO cname FROM pg_constraint
     WHERE conrelid = 'hora_nf_entrada_item'::regclass
       AND contype = 'f' AND confrelid = 'hora_moto'::regclass
     LIMIT 1;
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE hora_nf_entrada_item DROP CONSTRAINT %I', cname);
    END IF;
END $$;
"""


def _col_existe():
    row = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='hora_nf_entrada_item' AND column_name='desconsiderado'"
    )).first()
    return row is not None


def _fk_existe():
    row = db.session.execute(text(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid='hora_nf_entrada_item'::regclass AND contype='f' "
        "AND confrelid='hora_moto'::regclass LIMIT 1"
    )).first()
    return row[0] if row else None


def main():
    app = create_app()
    with app.app_context():
        print(f"[before] coluna desconsiderado existe: {_col_existe()}")
        print(f"[before] FK numero_chassi->hora_moto: {_fk_existe()}")
        db.session.execute(text(SQL_COLUNA))
        db.session.execute(text(SQL_INDEX))
        db.session.execute(text(SQL_DROP_FK))
        db.session.commit()
        print(f"[after] coluna desconsiderado existe: {_col_existe()}")
        print(f"[after] FK numero_chassi->hora_moto: {_fk_existe()}")
        assert _col_existe() is True, "coluna nao criada"
        assert _fk_existe() is None, "FK nao removida"
        print("OK — migration hora_43 aplicada.")


if __name__ == '__main__':
    main()
