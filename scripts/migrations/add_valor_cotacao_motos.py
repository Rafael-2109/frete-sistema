"""
Migration: Adicionar colunas valor_unitario e valor_total em carvia_cotacao_motos
Data: 2026-03-27
Motivo:
  Model CarviaCotacaoMoto declara valor_unitario e valor_total (models.py:1543-1544)
  mas a migration original (criar_tabelas_carvia_cotacao) nao incluiu essas colunas.
  Causa erro 500 em /carvia/cotacoes/<id> ao fazer cotacao.motos.all().
  Sentry: ProgrammingError — column carvia_cotacao_motos.valor_unitario does not exist
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    for coluna in ['valor_unitario', 'valor_total']:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = 'carvia_cotacao_motos' "
            f"  AND column_name = '{coluna}'"
            ")"
        ))
        print(f"[ANTES] carvia_cotacao_motos.{coluna} existe: {result.scalar()}")


def executar_migration(conn):
    """Executa DDL"""
    conn.execute(db.text("""
        ALTER TABLE carvia_cotacao_motos
            ADD COLUMN IF NOT EXISTS valor_unitario NUMERIC(15,2),
            ADD COLUMN IF NOT EXISTS valor_total NUMERIC(15,2)
    """))
    print("[OK] Colunas valor_unitario e valor_total adicionadas")


def verificar_depois(conn):
    """Verifica estado apos migration"""
    for coluna in ['valor_unitario', 'valor_total']:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = 'carvia_cotacao_motos' "
            f"  AND column_name = '{coluna}'"
            ")"
        ))
        print(f"[DEPOIS] carvia_cotacao_motos.{coluna} existe: {result.scalar()}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: Adicionar valor_unitario/valor_total em carvia_cotacao_motos")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
