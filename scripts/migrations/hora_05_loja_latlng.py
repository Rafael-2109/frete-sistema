"""Migration HORA 05: cache de latitude/longitude em hora_loja."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


COLUNAS = ['latitude', 'longitude', 'geocodado_em', 'geocoding_provider']


def coluna_existe(col: str) -> bool:
    result = db.session.execute(
        db.text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'hora_loja' AND column_name = :col
            """
        ),
        {'col': col},
    ).scalar()
    return result is not None


def verificar_antes():
    existentes = [c for c in COLUNAS if coluna_existe(c)]
    print(f"[BEFORE] colunas existentes: {len(existentes)}/{len(COLUNAS)}")


def executar_migration():
    sql_path = os.path.join(os.path.dirname(__file__), 'hora_05_loja_latlng.sql')
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    faltantes = [c for c in COLUNAS if not coluna_existe(c)]
    assert not faltantes, f"colunas faltando: {faltantes}"
    print(f"[AFTER] todas as {len(COLUNAS)} colunas existem")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 05 concluida")
