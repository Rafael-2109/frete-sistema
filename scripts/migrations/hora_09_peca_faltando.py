"""Migration HORA 09: cria hora_peca_faltando + foto."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


TABELAS = ['hora_peca_faltando', 'hora_peca_faltando_foto']


def tabela_existe(tbl: str) -> bool:
    result = db.session.execute(
        db.text(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_name = :tbl AND table_schema = 'public'
            """
        ),
        {'tbl': tbl},
    ).scalar()
    return result is not None


def verificar_antes():
    for t in TABELAS:
        print(f"[BEFORE] {t} existe? {tabela_existe(t)}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_09_peca_faltando.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    for t in TABELAS:
        assert tabela_existe(t), f"tabela {t} nao foi criada"
        print(f"[AFTER] {t} existe = True")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 09 concluida")
