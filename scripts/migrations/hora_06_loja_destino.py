"""Migration HORA 06: loja_destino_id em hora_pedido e hora_nf_entrada."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def coluna_existe(tabela: str, col: str) -> bool:
    result = db.session.execute(
        db.text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :col
            """
        ),
        {'tabela': tabela, 'col': col},
    ).scalar()
    return result is not None


def verificar_antes():
    p = coluna_existe('hora_pedido', 'loja_destino_id')
    n = coluna_existe('hora_nf_entrada', 'loja_destino_id')
    print(f"[BEFORE] hora_pedido.loja_destino_id: {'SIM' if p else 'NAO'}")
    print(f"[BEFORE] hora_nf_entrada.loja_destino_id: {'SIM' if n else 'NAO'}")


def executar_migration():
    sql_path = os.path.join(os.path.dirname(__file__), 'hora_06_loja_destino.sql')
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    assert coluna_existe('hora_pedido', 'loja_destino_id')
    assert coluna_existe('hora_nf_entrada', 'loja_destino_id')
    print("[AFTER] ambas colunas criadas + indices")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 06 concluida")
