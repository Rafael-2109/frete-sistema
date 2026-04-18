"""Migration HORA 03: sistema_lojas + loja_hora_id em usuarios."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def coluna_existe(col: str) -> bool:
    result = db.session.execute(
        db.text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'usuarios' AND column_name = :col
            """
        ),
        {'col': col},
    ).scalar()
    return result is not None


def verificar_antes():
    print(f"[BEFORE] sistema_lojas existe: {'SIM' if coluna_existe('sistema_lojas') else 'NAO'}")
    print(f"[BEFORE] loja_hora_id existe: {'SIM' if coluna_existe('loja_hora_id') else 'NAO'}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_03_usuario_sistema_lojas.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    assert coluna_existe('sistema_lojas'), "sistema_lojas nao criado"
    assert coluna_existe('loja_hora_id'), "loja_hora_id nao criado"
    print("[AFTER] sistema_lojas: SIM")
    print("[AFTER] loja_hora_id: SIM")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 03 concluida")
