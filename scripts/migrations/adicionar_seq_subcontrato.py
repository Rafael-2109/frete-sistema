"""
Migration: Adicionar numero_sequencial_transportadora em carvia_subcontratos
=============================================================================

Adiciona campo para numeracao sequencial por transportadora.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/adicionar_seq_subcontrato.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_antes():
    """Verifica estado antes da migration"""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos'
          AND column_name = 'numero_sequencial_transportadora'
    """)).fetchone()

    if result:
        print("[INFO] Campo numero_sequencial_transportadora ja existe. Migration nao necessaria.")
        return False

    print("[INFO] Campo numero_sequencial_transportadora NAO existe. Sera criado.")
    return True


def executar_migration():
    """Executa a migration"""
    # 1. Adicionar coluna
    print("[1/3] Adicionando coluna numero_sequencial_transportadora...")
    db.session.execute(text("""
        ALTER TABLE carvia_subcontratos
        ADD COLUMN IF NOT EXISTS numero_sequencial_transportadora INTEGER
    """))

    # 2. Criar indice unico composto
    print("[2/3] Criando indice unico composto...")
    db.session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_sub_transportadora_seq
        ON carvia_subcontratos(transportadora_id, numero_sequencial_transportadora)
        WHERE numero_sequencial_transportadora IS NOT NULL
    """))

    # 3. Preencher sequencial para subcontratos existentes
    print("[3/3] Preenchendo numero sequencial para subcontratos existentes...")
    db.session.execute(text("""
        WITH numbered AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY transportadora_id
                       ORDER BY criado_em, id
                   ) AS seq
            FROM carvia_subcontratos
            WHERE numero_sequencial_transportadora IS NULL
        )
        UPDATE carvia_subcontratos
        SET numero_sequencial_transportadora = numbered.seq
        FROM numbered
        WHERE carvia_subcontratos.id = numbered.id
    """))

    db.session.commit()
    print("[OK] Migration concluida com sucesso.")


def verificar_depois():
    """Verifica estado apos a migration"""
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos'
          AND column_name = 'numero_sequencial_transportadora'
    """)).fetchone()

    if result:
        print("[OK] Campo numero_sequencial_transportadora existe.")
    else:
        print("[ERRO] Campo NAO foi criado!")
        return False

    # Contar subcontratos com sequencial preenchido
    result = db.session.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(numero_sequencial_transportadora) AS com_seq
        FROM carvia_subcontratos
    """)).fetchone()

    if result:
        print(f"[INFO] Subcontratos: {result[0]} total, {result[1]} com sequencial preenchido.")
    return True


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        if not verificar_antes():
            sys.exit(0)

        executar_migration()
        verificar_depois()
