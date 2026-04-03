"""Migration: CarviaFrete.embarque_id nullable.

Permite criar CarviaFrete backfill sem embarque vinculado (historico pre-hook).
Tambem recria unique constraint como partial index (apenas WHERE embarque_id IS NOT NULL).
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    # Nullable
    is_nullable = db.session.execute(db.text("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'carvia_fretes' AND column_name = 'embarque_id'
    """)).scalar()
    print(f"[BEFORE] carvia_fretes.embarque_id is_nullable = {is_nullable}")

    # Constraint original
    constraint = db.session.execute(db.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'carvia_fretes'
        AND constraint_name = 'uq_carvia_frete_embarque_cnpj'
    """)).scalar()
    print(f"[BEFORE] constraint uq_carvia_frete_embarque_cnpj = {'existe' if constraint else 'NAO existe'}")

    # Partial index
    partial_idx = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_fretes'
        AND indexname = 'uq_carvia_frete_embarque_cnpj_notnull'
    """)).scalar()
    print(f"[BEFORE] partial index uq_carvia_frete_embarque_cnpj_notnull = {'existe' if partial_idx else 'NAO existe'}")

    return is_nullable


def executar_migration():
    """Executa a migration."""
    # 1. Tornar nullable
    db.session.execute(db.text("""
        ALTER TABLE carvia_fretes ALTER COLUMN embarque_id DROP NOT NULL
    """))
    print("[OK] embarque_id alterado para nullable")

    # 2. Dropar unique constraint original (se existe)
    constraint = db.session.execute(db.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'carvia_fretes'
        AND constraint_name = 'uq_carvia_frete_embarque_cnpj'
    """)).scalar()
    if constraint:
        db.session.execute(db.text("""
            ALTER TABLE carvia_fretes DROP CONSTRAINT uq_carvia_frete_embarque_cnpj
        """))
        print("[OK] Constraint uq_carvia_frete_embarque_cnpj removida")

    # 3. Recriar como partial unique index
    db.session.execute(db.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_frete_embarque_cnpj_notnull
            ON carvia_fretes (embarque_id, cnpj_emitente, cnpj_destino)
            WHERE embarque_id IS NOT NULL
    """))
    print("[OK] Partial unique index uq_carvia_frete_embarque_cnpj_notnull criado")

    db.session.commit()


def verificar_depois():
    """Verifica estado apos a migration."""
    # Nullable
    is_nullable = db.session.execute(db.text("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'carvia_fretes' AND column_name = 'embarque_id'
    """)).scalar()
    print(f"[AFTER] carvia_fretes.embarque_id is_nullable = {is_nullable}")

    # Partial index
    partial_idx = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_fretes'
        AND indexname = 'uq_carvia_frete_embarque_cnpj_notnull'
    """)).scalar()
    print(f"[AFTER] partial index uq_carvia_frete_embarque_cnpj_notnull = {'existe' if partial_idx else 'NAO existe'}")

    # Dados existentes
    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_fretes"
    )).scalar()
    com_emb = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_fretes WHERE embarque_id IS NOT NULL"
    )).scalar()
    print(f"[DATA] {com_emb}/{total} fretes com embarque_id preenchido")

    assert is_nullable == 'YES', f"Esperado 'YES', obtido '{is_nullable}'"
    assert partial_idx is not None, "Partial index nao foi criado"


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        antes = verificar_antes()
        if antes == 'YES':
            print("[SKIP] Ja e nullable — verificando partial index")
            # Garantir partial index mesmo se nullable ja estava OK
            db.session.execute(db.text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_frete_embarque_cnpj_notnull
                    ON carvia_fretes (embarque_id, cnpj_emitente, cnpj_destino)
                    WHERE embarque_id IS NOT NULL
            """))
            db.session.commit()
        else:
            executar_migration()
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
