"""Migration HORA 14: adiciona pode_aprovar em hora_user_permissao.

Permite delegar a acao 'Aprovar usuarios pendentes' para nao-admins via tela
de permissoes. Default = False (admin sempre passa, demais precisam liberacao).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(
        db.text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {'t': tabela, 'c': coluna},
    ).scalar())


def verificar_antes():
    print("[BEFORE]")
    print(f"  hora_user_permissao.pode_aprovar existe? "
          f"{coluna_existe('hora_user_permissao', 'pode_aprovar')}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_14_user_permissao_aprovar.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    assert coluna_existe('hora_user_permissao', 'pode_aprovar')
    print("[AFTER] pode_aprovar presente")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 14 concluida")
