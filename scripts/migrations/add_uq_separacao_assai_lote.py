"""Migration: UNIQUE partial index em separacao para lotes ASSAI-SEP-*.

Garantia atomica de idempotencia do mirror_assai_to_separacao
(`app/motos_assai/services/separacao_mirror_service.py`).

Sem este index, duas chamadas concorrentes de `finalizar_separacao` para
a mesma AssaiSeparacao (ex: double-tap em mobile, retry de network)
podem ambas passar o COUNT check e criar 2*N linhas em `separacao`,
duplicando totais quando `recalcular_totais_embarque` agregar.

Index UNIQUE parcial em (separacao_lote_id, cod_produto) WHERE lote
LIKE 'ASSAI-SEP-%' previne no nivel do banco. Linhas Nacom/CarVia nao
sao afetadas (postgresql_where).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def _index_existe(nome: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM pg_indexes WHERE indexname = :n
    """), {'n': nome}).scalar())


def verificar_antes():
    print(f"[BEFORE] uq_separacao_assai_lote_produto existe = "
          f"{_index_existe('uq_separacao_assai_lote_produto')}")


def executar_migration():
    if _index_existe('uq_separacao_assai_lote_produto'):
        print("[SKIP] index ja existe")
        return

    db.session.execute(db.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_separacao_assai_lote_produto
            ON separacao (separacao_lote_id, cod_produto)
            WHERE separacao_lote_id LIKE 'ASSAI-SEP-%'
    """))
    print("[OK] uq_separacao_assai_lote_produto criado")
    db.session.commit()


def verificar_depois():
    existe = _index_existe('uq_separacao_assai_lote_produto')
    print(f"[AFTER] uq_separacao_assai_lote_produto existe = {existe}")
    assert existe, "Index nao foi criado"

    total_assai = db.session.execute(db.text("""
        SELECT COUNT(*) FROM separacao
        WHERE separacao_lote_id LIKE 'ASSAI-SEP-%'
    """)).scalar()
    print(f"[DATA] {total_assai} linha(s) em separacao com prefix ASSAI-SEP-*")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration uq_separacao_assai_lote_produto concluida")
