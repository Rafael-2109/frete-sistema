"""
Migration: Criar tabela carvia_config — parametros globais chave-valor
Data: 2026-03-20
Descricao:
  - carvia_config: parametros globais do modulo CarVia (limite desconto, etc.)
  - Seed: limite_desconto_percentual=5.0
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_config'"
        ")"
    ))
    existe = result.scalar()
    print(f"[ANTES] carvia_config existe: {existe}")
    return existe


def executar_migration(conn):
    """Executa DDL + seed"""
    # 1. Tabela
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_config (
            id SERIAL PRIMARY KEY,
            chave VARCHAR(50) NOT NULL UNIQUE,
            valor TEXT NOT NULL,
            descricao VARCHAR(255),
            atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_por VARCHAR(100) NOT NULL
        )
    """))
    print("[OK] carvia_config criada")

    # 2. Seed: limite_desconto_percentual
    result = conn.execute(db.text(
        "SELECT 1 FROM carvia_config WHERE chave = 'limite_desconto_percentual'"
    ))
    if not result.fetchone():
        conn.execute(db.text("""
            INSERT INTO carvia_config (chave, valor, descricao, atualizado_por)
            VALUES (
                'limite_desconto_percentual',
                '5.0',
                'Limite percentual de desconto que Jessica pode aprovar sem admin',
                'migration'
            )
        """))
        print("[OK] Seed limite_desconto_percentual=5.0 inserido")
    else:
        print("[SKIP] Seed limite_desconto_percentual ja existe")


def verificar_depois(conn):
    """Verifica estado apos migration"""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.tables "
        "  WHERE table_name = 'carvia_config'"
        ")"
    ))
    print(f"[DEPOIS] carvia_config existe: {result.scalar()}")

    result = conn.execute(db.text(
        "SELECT chave, valor FROM carvia_config ORDER BY chave"
    ))
    for row in result:
        print(f"  {row[0]} = {row[1]}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: Criar tabela carvia_config")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
