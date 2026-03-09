"""
Migration: Backfill prefixo SC-### → COTACAO-### em carvia_sessoes_cotacao
==========================================================================

Renomeia sessoes existentes de SC-001 para COTACAO-001, etc.
DML apenas (sem DDL).

Executar: python scripts/migrations/backfill_prefixo_cotacao_carvia.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            # Verificar quantas sessoes com prefixo SC- existem
            result = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_sessoes_cotacao "
                "WHERE numero_sessao LIKE 'SC-%'"
            ))
            count_antes = result.scalar()
            print(f"Sessoes com prefixo SC-: {count_antes}")

            if count_antes == 0:
                print("Nenhuma sessao para migrar.")
                return

            # Listar antes
            result = conn.execute(text(
                "SELECT id, numero_sessao FROM carvia_sessoes_cotacao "
                "WHERE numero_sessao LIKE 'SC-%' ORDER BY id"
            ))
            for row in result:
                novo = row.numero_sessao.replace('SC-', 'COTACAO-')
                print(f"  {row.id}: {row.numero_sessao} -> {novo}")

            # Executar backfill
            result = conn.execute(text(
                "UPDATE carvia_sessoes_cotacao "
                "SET numero_sessao = REPLACE(numero_sessao, 'SC-', 'COTACAO-') "
                "WHERE numero_sessao LIKE 'SC-%'"
            ))
            print(f"\n{result.rowcount} sessoes atualizadas.")

            # Verificar apos
            result = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_sessoes_cotacao "
                "WHERE numero_sessao LIKE 'SC-%'"
            ))
            restantes = result.scalar()
            print(f"Sessoes restantes com SC-: {restantes}")

            result = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_sessoes_cotacao "
                "WHERE numero_sessao LIKE 'COTACAO-%'"
            ))
            migradas = result.scalar()
            print(f"Sessoes com COTACAO-: {migradas}")

    print("\nBackfill concluido!")


if __name__ == '__main__':
    run()
