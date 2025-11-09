"""
Script de Migração: Adicionar Índices de Performance
Data: 2025-01-08
Objetivo: Otimizar queries da Necessidade de Produção

ÍNDICES A SEREM CRIADOS:
1. idx_carteira_produto_data - (cod_produto, data_pedido) em carteira_principal
2. idx_separacao_sync_only - (sincronizado_nf) parcial em separacao

IMPACTO ESPERADO:
- Redução de 60-80% no tempo de queries com filtro por produto + data
- Otimização de queries que filtram apenas por sincronizado_nf
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_indices():
    """Adiciona índices de performance"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 70)
            print("ADICIONANDO ÍNDICES DE PERFORMANCE")
            print("=" * 70)

            # 1. Verificar se índice já existe em carteira_principal
            print("\n[1/2] Verificando índice idx_carteira_produto_data...")
            resultado = db.session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'carteira_principal'
                AND indexname = 'idx_carteira_produto_data'
            """)).fetchone()

            if resultado:
                print("   ⚠️  Índice idx_carteira_produto_data JÁ EXISTE. Pulando...")
            else:
                print("   ✅ Criando índice composto (cod_produto, data_pedido)...")
                print("   ⏳ AVISO: Sem CONCURRENTLY - pode bloquear tabela brevemente")

                # Criar índice SEM CONCURRENTLY (evita erro de transação)
                db.session.execute(text("""
                    CREATE INDEX idx_carteira_produto_data
                    ON carteira_principal (cod_produto, data_pedido)
                """))
                db.session.commit()
                print("   ✅ Índice idx_carteira_produto_data criado com sucesso!")

            # 2. Verificar se índice já existe em separacao
            print("\n[2/2] Verificando índice idx_separacao_sync_only...")
            resultado = db.session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'separacao'
                AND indexname = 'idx_separacao_sync_only'
            """)).fetchone()

            if resultado:
                print("   ⚠️  Índice idx_separacao_sync_only JÁ EXISTE. Pulando...")
            else:
                print("   ✅ Criando índice parcial em sincronizado_nf...")
                print("   ⏳ AVISO: Sem CONCURRENTLY - pode bloquear tabela brevemente")

                # Criar índice parcial SEM CONCURRENTLY
                db.session.execute(text("""
                    CREATE INDEX idx_separacao_sync_only
                    ON separacao (sincronizado_nf)
                    WHERE sincronizado_nf = FALSE
                """))
                db.session.commit()
                print("   ✅ Índice idx_separacao_sync_only criado com sucesso!")

            print("\n" + "=" * 70)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 70)
            print("\nINFORMAÇÕES IMPORTANTES:")
            print("- Os índices foram criados SEM CONCURRENTLY (mais simples)")
            print("- idx_carteira_produto_data: Otimiza queries com filtro por produto + data")
            print("- idx_separacao_sync_only: Índice PARCIAL que otimiza sincronizado_nf=FALSE")
            print("\nIMPACTO ESPERADO:")
            print("- Redução de 60-80% no tempo de cálculo de necessidade de produção")
            print("- Queries mais rápidas em projeção de estoque")
            print("=" * 70)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO ao criar índices: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    adicionar_indices()
