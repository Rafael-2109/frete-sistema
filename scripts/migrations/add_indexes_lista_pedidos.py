"""
Adiciona partial indexes para otimizar a rota lista_pedidos.
Campos falta_item, falta_pagamento e nf_cd na tabela separacao.

Uso local:
    source .venv/bin/activate
    python scripts/migrations/add_indexes_lista_pedidos.py

Uso Render Shell (SQL direto):
    Executar os comandos SQL do arquivo add_indexes_lista_pedidos.sql
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app import create_app, db
from sqlalchemy import text


def criar_indexes():
    app = create_app()
    with app.app_context():
        indexes = [
            (
                'idx_sep_falta_item_sync',
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_falta_item_sync "
                "ON separacao (falta_item, sincronizado_nf) WHERE falta_item = true"
            ),
            (
                'idx_sep_falta_pgto_sync',
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_falta_pgto_sync "
                "ON separacao (falta_pagamento, sincronizado_nf) WHERE falta_pagamento = true"
            ),
            (
                'idx_sep_nf_cd',
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_nf_cd "
                "ON separacao (nf_cd) WHERE nf_cd = true"
            ),
        ]

        for nome, sql in indexes:
            try:
                # CONCURRENTLY requer autocommit (fora de transacao)
                connection = db.engine.connect()
                connection.execution_options(isolation_level="AUTOCOMMIT")
                connection.execute(text(sql))
                connection.close()
                print(f"  ✅ Index {nome} criado com sucesso")
            except Exception as e:
                if 'already exists' in str(e).lower():
                    print(f"  ⏭️  Index {nome} ja existe, pulando")
                else:
                    print(f"  ❌ Erro ao criar index {nome}: {e}")

        print("\n🎯 Indexes para lista_pedidos criados!")


if __name__ == '__main__':
    criar_indexes()
