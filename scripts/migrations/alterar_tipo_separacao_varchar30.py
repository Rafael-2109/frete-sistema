"""
Migration: Alterar tipo_separacao de VARCHAR(10) para VARCHAR(30)
Tabela: alertas_separacao_cotada
Motivo: Sentry PYTHON-FLASK-A/X — DataError "value too long for type character varying(10)"
Data: 2026-03-11
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_estado(conn):
    """Verifica o tamanho atual da coluna tipo_separacao."""
    result = conn.execute(text("""
        SELECT character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'alertas_separacao_cotada'
          AND column_name = 'tipo_separacao'
    """))
    row = result.fetchone()
    if row:
        return row[0]
    return None


def executar_migration():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Before
            tamanho_antes = verificar_estado(conn)
            print(f"[BEFORE] tipo_separacao: VARCHAR({tamanho_antes})")

            if tamanho_antes == 10:
                conn.execute(text(
                    "ALTER TABLE alertas_separacao_cotada "
                    "ALTER COLUMN tipo_separacao TYPE VARCHAR(30)"
                ))
                conn.commit()
                print("[OK] tipo_separacao alterado para VARCHAR(30)")
            elif tamanho_antes == 30:
                print("[SKIP] tipo_separacao ja e VARCHAR(30)")
                return
            else:
                print(f"[WARN] Tamanho inesperado: {tamanho_antes}")
                return

            # After
            tamanho_depois = verificar_estado(conn)
            print(f"[AFTER] tipo_separacao: VARCHAR({tamanho_depois})")
            assert tamanho_depois == 30, f"Esperado 30, obteve {tamanho_depois}"
            print("[SUCCESS] Migration concluida com sucesso")


if __name__ == '__main__':
    executar_migration()
