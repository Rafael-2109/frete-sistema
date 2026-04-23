"""Migration HORA 10: amplia hora_pedido.status VARCHAR(20) -> VARCHAR(30).

Motivo: valor 'PARCIALMENTE_FATURADO' (22 char) excede o tamanho original.
Bug em producao em /hora/nfs/upload:
    psycopg2.errors.StringDataRightTruncation: value too long for
    type character varying(20)
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


TABELA = 'hora_pedido'
COLUNA = 'status'
TAMANHO_ALVO = 30


def tamanho_atual() -> int | None:
    result = db.session.execute(
        db.text(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {'t': TABELA, 'c': COLUNA},
    ).scalar()
    return result


def verificar_antes():
    tamanho = tamanho_atual()
    print(f"[BEFORE] {TABELA}.{COLUNA} VARCHAR({tamanho})")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_10_pedido_status_varchar30.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    tamanho = tamanho_atual()
    assert tamanho is not None and tamanho >= TAMANHO_ALVO, (
        f"coluna {TABELA}.{COLUNA} esta em VARCHAR({tamanho}), "
        f"esperado >= VARCHAR({TAMANHO_ALVO})"
    )
    print(f"[AFTER] {TABELA}.{COLUNA} VARCHAR({tamanho}) — OK")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 10 concluida")
