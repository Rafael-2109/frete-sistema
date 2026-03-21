"""
Migration: Adicionar campos provisorio e carvia_cotacao_id em embarque_itens
============================================================================

Suporte a itens provisorios CarVia em embarques.
- provisorio (BOOLEAN DEFAULT FALSE): placeholder de cotacao aguardando pedidos/NF
- carvia_cotacao_id (INTEGER NULL): rastreabilidade da cotacao CarVia de origem
- 2 indices parciais para busca eficiente

Uso: python scripts/migrations/adicionar_provisorio_embarque_item.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'embarque_itens'
        AND column_name IN ('provisorio', 'carvia_cotacao_id')
        ORDER BY column_name
    """))
    existentes = [r[0] for r in result]
    print(f"[ANTES] Campos ja existentes: {existentes or 'NENHUM'}")
    return existentes


def executar_migration():
    """Executa a migration."""
    # Campo provisorio
    db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'embarque_itens' AND column_name = 'provisorio'
            ) THEN
                ALTER TABLE embarque_itens
                    ADD COLUMN provisorio BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
    """))
    print("[OK] Campo provisorio adicionado (ou ja existia)")

    # Campo carvia_cotacao_id
    db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'embarque_itens' AND column_name = 'carvia_cotacao_id'
            ) THEN
                ALTER TABLE embarque_itens
                    ADD COLUMN carvia_cotacao_id INTEGER NULL;
            END IF;
        END $$;
    """))
    print("[OK] Campo carvia_cotacao_id adicionado (ou ja existia)")

    # Indice parcial para provisorios
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_embarque_itens_provisorio
            ON embarque_itens (embarque_id)
            WHERE provisorio = TRUE;
    """))
    print("[OK] Indice ix_embarque_itens_provisorio criado")

    # Indice parcial para carvia_cotacao_id
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_embarque_itens_carvia_cotacao
            ON embarque_itens (carvia_cotacao_id)
            WHERE carvia_cotacao_id IS NOT NULL;
    """))
    print("[OK] Indice ix_embarque_itens_carvia_cotacao criado")

    db.session.commit()


def verificar_depois():
    """Verifica estado apos a migration."""
    result = db.session.execute(text("""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'embarque_itens'
        AND column_name IN ('provisorio', 'carvia_cotacao_id')
        ORDER BY column_name
    """))
    for row in result:
        print(f"  {row[0]}: {row[1]} default={row[2]} nullable={row[3]}")

    # Contar registros existentes (todos devem ter provisorio=FALSE)
    count = db.session.execute(text(
        "SELECT COUNT(*) FROM embarque_itens WHERE provisorio = TRUE"
    )).scalar()
    print(f"[DEPOIS] Itens provisorios existentes: {count} (esperado: 0)")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: adicionar_provisorio_embarque_item")
        print("=" * 60)

        existentes = verificar_antes()

        if len(existentes) == 2:
            print("[SKIP] Ambos campos ja existem. Migration idempotente.")
        else:
            executar_migration()

        verificar_depois()
        print("[CONCLUIDO]")
