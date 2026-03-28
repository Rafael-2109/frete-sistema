"""
Migration: adicionar_frete_id_subcontrato
==========================================
Adiciona coluna frete_id em carvia_subcontratos para suportar
N subcontratos por frete (multi-leg transport).

Inverte a FK: ao inves de CarviaFrete.subcontrato_id (1:1),
usa CarviaSubcontrato.frete_id (N:1).

Data: 2026-03-28
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos'
          AND column_name = 'frete_id'
    """)).fetchone()

    if result:
        print("[INFO] Coluna frete_id JA existe em carvia_subcontratos — migration idempotente")
        return True  # ja existe
    else:
        print("[INFO] Coluna frete_id NAO existe — sera criada")
        return False


def aplicar_ddl():
    """Adiciona coluna frete_id + indice."""
    db.session.execute(text("""
        ALTER TABLE carvia_subcontratos
        ADD COLUMN IF NOT EXISTS frete_id INTEGER REFERENCES carvia_fretes(id)
    """))

    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_subcontratos_frete_id
        ON carvia_subcontratos(frete_id)
    """))

    db.session.commit()
    print("[OK] Coluna frete_id + indice criados")


def backfill():
    """Popula frete_id a partir de CarviaFrete.subcontrato_id existente."""
    result = db.session.execute(text("""
        UPDATE carvia_subcontratos s
        SET frete_id = f.id
        FROM carvia_fretes f
        WHERE f.subcontrato_id = s.id
          AND s.frete_id IS NULL
    """))

    db.session.commit()
    print(f"[OK] Backfill: {result.rowcount} subcontratos atualizados com frete_id")


def verificar_depois():
    """Verifica consistencia apos migration."""
    # 1. Coluna existe?
    col = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos'
          AND column_name = 'frete_id'
    """)).fetchone()

    if not col:
        print("[ERRO] Coluna frete_id NAO foi criada!")
        return False

    # 2. Indice existe?
    idx = db.session.execute(text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'carvia_subcontratos'
          AND indexname = 'ix_carvia_subcontratos_frete_id'
    """)).fetchone()

    if not idx:
        print("[ERRO] Indice ix_carvia_subcontratos_frete_id NAO foi criado!")
        return False

    # 3. Inconsistencias (fretes com subcontrato_id mas sub sem frete_id)?
    inconsistentes = db.session.execute(text("""
        SELECT COUNT(*)
        FROM carvia_fretes f
        JOIN carvia_subcontratos s ON f.subcontrato_id = s.id
        WHERE s.frete_id IS NULL
    """)).scalar()

    if inconsistentes > 0:
        print(f"[AVISO] {inconsistentes} subcontratos com frete vinculado mas frete_id NULL")
    else:
        print("[OK] Todos subcontratos vinculados tem frete_id populado")

    # 4. Contagem total
    total = db.session.execute(text("""
        SELECT COUNT(*) FROM carvia_subcontratos WHERE frete_id IS NOT NULL
    """)).scalar()
    print(f"[INFO] Total subcontratos com frete_id: {total}")

    return True


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: adicionar_frete_id_subcontrato")
        print("=" * 60)

        ja_existe = verificar_antes()

        if not ja_existe:
            aplicar_ddl()

        backfill()
        ok = verificar_depois()

        if ok:
            print("\n[SUCESSO] Migration concluida com sucesso")
        else:
            print("\n[FALHA] Migration com problemas — verificar logs")
            sys.exit(1)


if __name__ == '__main__':
    main()
