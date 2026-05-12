"""Migration: adicionar fretes.origem (NACOM | OP_ASSAI).

Identifica origem do Frete para flag visivel em Lancamento Freteiros,
exportacao de fechamento e relatorios. Default 'NACOM' preserva fretes
existentes inalterados.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def _coluna_existe(coluna: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'fretes' AND column_name = :c
    """), {'c': coluna}).scalar())


def _index_existe(nome: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM pg_indexes WHERE indexname = :n
    """), {'n': nome}).scalar())


def verificar_antes():
    print(f"[BEFORE] fretes.origem existe = {_coluna_existe('origem')}")
    print(f"[BEFORE] idx_fretes_origem existe = {_index_existe('idx_fretes_origem')}")


def executar_migration():
    if not _coluna_existe('origem'):
        db.session.execute(db.text("""
            ALTER TABLE fretes
            ADD COLUMN origem VARCHAR(20) NOT NULL DEFAULT 'NACOM'
        """))
        print("[OK] fretes.origem adicionado (default 'NACOM')")
    else:
        print("[SKIP] fretes.origem ja existe")

    if not _index_existe('idx_fretes_origem'):
        db.session.execute(db.text("""
            CREATE INDEX idx_fretes_origem ON fretes (origem)
        """))
        print("[OK] idx_fretes_origem criado")
    else:
        print("[SKIP] idx_fretes_origem ja existe")

    db.session.commit()


def verificar_depois():
    assert _coluna_existe('origem'), "Coluna origem nao foi criada"
    assert _index_existe('idx_fretes_origem'), "Index nao foi criado"

    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM fretes"
    )).scalar()
    nacom = db.session.execute(db.text(
        "SELECT COUNT(*) FROM fretes WHERE origem = 'NACOM'"
    )).scalar()
    assai = db.session.execute(db.text(
        "SELECT COUNT(*) FROM fretes WHERE origem = 'OP_ASSAI'"
    )).scalar()
    print(f"[DATA] total={total} | NACOM={nacom} | OP_ASSAI={assai}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration fretes.origem concluida")
