"""
Script para criação de índices de otimização do módulo comercial
================================================================

Execute este script localmente para criar os índices de performance.

Uso:
    python scripts/otimizacao_indices_comercial.py

Autor: Sistema de Fretes
Data: 2025-01-21
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def criar_indices_otimizacao():
    """Cria índices para otimização do módulo comercial"""
    app = create_app()

    indices = [
        # Índices para entregas_monitoradas
        {
            'nome': 'idx_entregas_status_finalizacao',
            'tabela': 'entregas_monitoradas',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entregas_status_finalizacao
                ON entregas_monitoradas (status_finalizacao)
            '''
        },
        {
            'nome': 'idx_entregas_nf_status',
            'tabela': 'entregas_monitoradas',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entregas_nf_status
                ON entregas_monitoradas (numero_nf, status_finalizacao)
            '''
        },
        {
            'nome': 'idx_entregas_nao_entregues',
            'tabela': 'entregas_monitoradas',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entregas_nao_entregues
                ON entregas_monitoradas (numero_nf, cnpj_cliente)
                WHERE status_finalizacao IS NULL OR status_finalizacao != 'Entregue'
            '''
        },

        # Índices para faturamento_produto
        {
            'nome': 'idx_faturamento_equipe_status',
            'tabela': 'faturamento_produto',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_equipe_status
                ON faturamento_produto (equipe_vendas, status_nf)
            '''
        },
        {
            'nome': 'idx_faturamento_equipe_vendedor',
            'tabela': 'faturamento_produto',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_equipe_vendedor
                ON faturamento_produto (equipe_vendas, vendedor)
            '''
        },
        {
            'nome': 'idx_faturamento_nf_equipe',
            'tabela': 'faturamento_produto',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_nf_equipe
                ON faturamento_produto (numero_nf, equipe_vendas)
            '''
        },

        # Índices para carteira_principal
        {
            'nome': 'idx_carteira_equipe_vendedor',
            'tabela': 'carteira_principal',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_equipe_vendedor
                ON carteira_principal (equipe_vendas, vendedor)
                WHERE equipe_vendas IS NOT NULL AND vendedor IS NOT NULL
            '''
        },

        # Índices para cadastro_palletizacao
        {
            'nome': 'idx_palletizacao_cod_produto',
            'tabela': 'cadastro_palletizacao',
            'sql': '''
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_palletizacao_cod_produto
                ON cadastro_palletizacao (cod_produto)
            '''
        },
    ]

    with app.app_context():
        print("=" * 70)
        print("CRIAÇÃO DE ÍNDICES DE OTIMIZAÇÃO - MÓDULO COMERCIAL")
        print("=" * 70)
        print()

        # Verificar índices existentes
        resultado_existentes = db.session.execute(text("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname LIKE 'idx_%'
        """))
        indices_existentes = {row[0]: row[1] for row in resultado_existentes}

        sucesso = 0
        ja_existe = 0
        erro = 0

        for idx in indices:
            print(f"Processando: {idx['nome']} ({idx['tabela']})")

            if idx['nome'] in indices_existentes:
                print(f"  -> Já existe, pulando...")
                ja_existe += 1
                continue

            try:
                # IMPORTANTE: CREATE INDEX CONCURRENTLY não pode rodar em transação
                # Precisamos usar autocommit
                connection = db.engine.raw_connection()
                connection.set_isolation_level(0)  # AUTOCOMMIT
                cursor = connection.cursor()

                cursor.execute(idx['sql'])
                cursor.close()
                connection.close()

                print(f"  -> CRIADO com sucesso!")
                sucesso += 1

            except Exception as e:
                print(f"  -> ERRO: {e}")
                erro += 1

        print()
        print("=" * 70)
        print(f"RESUMO:")
        print(f"  - Índices criados: {sucesso}")
        print(f"  - Já existentes: {ja_existe}")
        print(f"  - Erros: {erro}")
        print("=" * 70)

        # Executar ANALYZE
        if sucesso > 0:
            print()
            print("Executando ANALYZE nas tabelas afetadas...")
            tabelas_afetadas = list(set(idx['tabela'] for idx in indices))
            for tabela in tabelas_afetadas:
                try:
                    db.session.execute(text(f"ANALYZE {tabela}"))
                    print(f"  -> ANALYZE {tabela}: OK")
                except Exception as e:
                    print(f"  -> ANALYZE {tabela}: ERRO - {e}")

            db.session.commit()
            print("ANALYZE concluído!")


if __name__ == '__main__':
    criar_indices_otimizacao()
