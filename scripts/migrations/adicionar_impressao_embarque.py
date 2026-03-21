"""
Migration: Adicionar campos de auditoria de impressao em embarques
==================================================================

Rastreamento de impressao e flag de reimpressao necessaria.
- impresso_em (TIMESTAMP NULL): timestamp da ultima impressao
- impresso_por (VARCHAR(100) NULL): usuario que imprimiu
- alterado_apos_impressao (BOOLEAN DEFAULT FALSE): embarque mudou apos impressao
- 1 indice parcial para busca de embarques que precisam reimprimir

Uso: python scripts/migrations/adicionar_impressao_embarque.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


CAMPOS = ('impresso_em', 'impresso_por', 'alterado_apos_impressao')


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'embarques'
        AND column_name IN ('impresso_em', 'impresso_por', 'alterado_apos_impressao')
        ORDER BY column_name
    """))
    existentes = [r[0] for r in result]
    print(f"[ANTES] Campos ja existentes: {existentes or 'NENHUM'}")
    return existentes


def executar_migration():
    """Executa a migration."""
    # Campo impresso_em
    db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'embarques' AND column_name = 'impresso_em'
            ) THEN
                ALTER TABLE embarques
                    ADD COLUMN impresso_em TIMESTAMP NULL;
            END IF;
        END $$;
    """))
    print("[OK] Campo impresso_em adicionado (ou ja existia)")

    # Campo impresso_por
    db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'embarques' AND column_name = 'impresso_por'
            ) THEN
                ALTER TABLE embarques
                    ADD COLUMN impresso_por VARCHAR(100) NULL;
            END IF;
        END $$;
    """))
    print("[OK] Campo impresso_por adicionado (ou ja existia)")

    # Campo alterado_apos_impressao
    db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'embarques' AND column_name = 'alterado_apos_impressao'
            ) THEN
                ALTER TABLE embarques
                    ADD COLUMN alterado_apos_impressao BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
    """))
    print("[OK] Campo alterado_apos_impressao adicionado (ou ja existia)")

    # Indice parcial para embarques que precisam reimprimir
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_embarques_precisa_reimprimir
            ON embarques (id)
            WHERE alterado_apos_impressao = TRUE AND impresso_em IS NOT NULL;
    """))
    print("[OK] Indice ix_embarques_precisa_reimprimir criado")

    db.session.commit()


def verificar_depois():
    """Verifica estado apos a migration."""
    result = db.session.execute(text("""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'embarques'
        AND column_name IN ('impresso_em', 'impresso_por', 'alterado_apos_impressao')
        ORDER BY column_name
    """))
    for row in result:
        print(f"  {row[0]}: {row[1]} default={row[2]} nullable={row[3]}")

    # Contar registros existentes (todos devem ter alterado_apos_impressao=FALSE)
    count = db.session.execute(text(
        "SELECT COUNT(*) FROM embarques WHERE alterado_apos_impressao = TRUE"
    )).scalar()
    print(f"[DEPOIS] Embarques com alterado_apos_impressao=TRUE: {count} (esperado: 0)")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: adicionar_impressao_embarque")
        print("=" * 60)

        existentes = verificar_antes()

        if len(existentes) == len(CAMPOS):
            print("[SKIP] Todos campos ja existem. Migration idempotente.")
        else:
            executar_migration()

        verificar_depois()
        print("[CONCLUIDO]")
