"""
Migration: Adicionar campos de contato do cliente em carvia_sessoes_cotacao
===========================================================================

Novos campos opcionais para identificar o cliente na sessao de cotacao:
- cliente_nome, cliente_email, cliente_telefone, cliente_responsavel

Executar: python scripts/migrations/adicionar_contato_sessao_cotacao_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se coluna existe na tabela"""
    result = conn.execute(text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = :tabela AND column_name = :coluna"
        ")"
    ), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def run():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            tabela = 'carvia_sessoes_cotacao'

            campos = [
                ('cliente_nome', 'VARCHAR(255)'),
                ('cliente_email', 'VARCHAR(255)'),
                ('cliente_telefone', 'VARCHAR(50)'),
                ('cliente_responsavel', 'VARCHAR(255)'),
            ]

            for nome_col, tipo in campos:
                if verificar_coluna_existe(conn, tabela, nome_col):
                    print(f"  [SKIP] Coluna {nome_col} ja existe em {tabela}")
                else:
                    conn.execute(text(
                        f"ALTER TABLE {tabela} ADD COLUMN {nome_col} {tipo}"
                    ))
                    print(f"  [OK] Coluna {nome_col} adicionada em {tabela}")

            # Verificacao
            for nome_col, _ in campos:
                existe = verificar_coluna_existe(conn, tabela, nome_col)
                status = 'OK' if existe else 'FALHOU'
                print(f"  [{status}] {tabela}.{nome_col}")

    print("\nMigration concluida!")


if __name__ == '__main__':
    run()
