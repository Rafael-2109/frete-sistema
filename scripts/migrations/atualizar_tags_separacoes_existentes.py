"""
Migration: Atualizar tags_pedido nas separações existentes
Data: 2026-02-04
Descrição: Popula o campo tags_pedido em separacao com dados de carteira_principal
           para separações que já existiam antes da feature de tags.

Executar localmente:
    source .venv/bin/activate
    python scripts/migrations/atualizar_tags_separacoes_existentes.py

Executar no Render Shell:
    python scripts/migrations/atualizar_tags_separacoes_existentes.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def atualizar_tags_separacoes():
    app = create_app()
    with app.app_context():
        try:
            # Contar separações sem tags
            result_antes = db.session.execute(text("""
                SELECT count(*) FROM separacao WHERE tags_pedido IS NULL
            """))
            total_sem_tags = result_antes.scalar()
            print(f"📋 Separações sem tags_pedido: {total_sem_tags}")

            # Contar pedidos com tags na carteira
            result_com_tags = db.session.execute(text("""
                SELECT count(DISTINCT num_pedido)
                FROM carteira_principal
                WHERE tags_pedido IS NOT NULL
            """))
            pedidos_com_tags = result_com_tags.scalar()
            print(f"🏷️ Pedidos com tags na carteira: {pedidos_com_tags}")

            if pedidos_com_tags == 0:
                print("⚠️ Nenhum pedido com tags na carteira. Nada a atualizar.")
                return

            # Atualizar separações com tags dos pedidos
            result = db.session.execute(text("""
                UPDATE separacao s
                SET tags_pedido = sub.tags_pedido
                FROM (
                    SELECT DISTINCT ON (num_pedido) num_pedido, tags_pedido
                    FROM carteira_principal
                    WHERE tags_pedido IS NOT NULL
                    ORDER BY num_pedido, id
                ) sub
                WHERE s.num_pedido = sub.num_pedido
                AND s.tags_pedido IS NULL
            """))

            atualizados = result.rowcount
            db.session.commit()

            print(f"✅ {atualizados} separações atualizadas com tags do pedido!")

            # Verificação
            result_depois = db.session.execute(text("""
                SELECT count(*) FROM separacao WHERE tags_pedido IS NOT NULL
            """))
            total_com_tags = result_depois.scalar()
            print(f"📊 Total de separações com tags agora: {total_com_tags}")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    atualizar_tags_separacoes()
