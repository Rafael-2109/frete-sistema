"""Migration HORA 07: adiciona qtd_declarada_itens em hora_nf_entrada."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


COLUNA = 'qtd_declarada_itens'


def coluna_existe(col: str) -> bool:
    result = db.session.execute(
        db.text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'hora_nf_entrada' AND column_name = :col
            """
        ),
        {'col': col},
    ).scalar()
    return result is not None


def verificar_antes():
    print(f"[BEFORE] {COLUNA} existe? {coluna_existe(COLUNA)}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_07_nf_entrada_qtd_declarada.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    assert coluna_existe(COLUNA), f"coluna {COLUNA} nao foi criada"
    print(f"[AFTER] {COLUNA} existe = True")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 07 concluida")
