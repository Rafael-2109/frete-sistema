"""
Migration: Cria 7 tabelas + indices + trigger FTS do modulo chat in-app.

Data: 2026-04-23
Fonte de verdade: app/chat/models.py

Tabelas criadas:
    chat_threads, chat_messages, chat_members,
    chat_attachments, chat_mentions, chat_reactions, chat_forwards

Nota: usa exec_driver_sql para garantir execucao de multi-statement DDL
com psycopg2 (alternativa mais robusta que text() para blocos SQL inteiros).
"""

import sys
import os
from pathlib import Path
from sqlalchemy import text

# sys.path.insert OBRIGATORIO antes de `from app import ...` (prod Render).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402

TABLES = [
    'chat_threads',
    'chat_messages',
    'chat_members',
    'chat_attachments',
    'chat_mentions',
    'chat_reactions',
    'chat_forwards',
]


def table_exists(conn, name: str) -> bool:
    result = conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :name AND table_schema = 'public'"),
        {'name': name},
    ).fetchone()
    return result is not None


def check_tables(conn, label: str) -> list[str]:
    print(f'=== {label} ===')
    missing = []
    for t in TABLES:
        exists = table_exists(conn, t)
        print(f'  {t}: {"YES" if exists else "NO"}')
        if not exists:
            missing.append(t)
    return missing


def main():
    app = create_app()
    with app.app_context():
        sql_path = Path(__file__).with_suffix('.sql')
        if not sql_path.exists():
            raise FileNotFoundError(f'SQL nao encontrado: {sql_path}')

        with sql_path.open() as f:
            ddl = f.read()

        with db.engine.connect() as conn:
            check_tables(conn, 'BEFORE')

            print('\nExecutando DDL...')
            # exec_driver_sql envia raw SQL direto ao psycopg2, garantindo
            # execucao correta de multi-statement dentro de BEGIN/COMMIT.
            conn.exec_driver_sql(ddl)

            print()
            missing_after = check_tables(conn, 'AFTER')

            if missing_after:
                raise SystemExit(f'ERRO: Tabelas nao criadas: {missing_after}')

        print('\nMigration concluida com sucesso.')


if __name__ == '__main__':
    main()
