#!/usr/bin/env python
"""
Script para adicionar colunas de sincronização na tabela Separacao
Usa a conexão existente do sistema (sem precisar de senha)
"""

from app import create_app, db
from sqlalchemy import text
import sys

def aplicar_migrations():
    """Aplica as alterações no banco de dados"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 60)
            print("🔧 ADICIONANDO COLUNAS DE SINCRONIZAÇÃO")
            print("=" * 60)
            
            # SQL para adicionar colunas
            sql_commands = [
                # Adicionar colunas
                """
                ALTER TABLE separacao 
                ADD COLUMN IF NOT EXISTS sincronizado_nf BOOLEAN DEFAULT FALSE
                """,
                """
                ALTER TABLE separacao 
                ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20)
                """,
                """
                ALTER TABLE separacao 
                ADD COLUMN IF NOT EXISTS data_sincronizacao TIMESTAMP
                """,
                """
                ALTER TABLE separacao 
                ADD COLUMN IF NOT EXISTS zerado_por_sync BOOLEAN DEFAULT FALSE
                """,
                """
                ALTER TABLE separacao 
                ADD COLUMN IF NOT EXISTS data_zeragem TIMESTAMP
                """,
                
                # Criar índices
                """
                CREATE INDEX IF NOT EXISTS idx_separacao_sincronizado_nf 
                ON separacao(sincronizado_nf)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_separacao_numero_nf 
                ON separacao(numero_nf)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_separacao_zerado_por_sync 
                ON separacao(zerado_por_sync)
                """
            ]
            
            # Executar cada comando
            for i, sql in enumerate(sql_commands, 1):
                try:
                    print(f"📝 Executando comando {i}/8...")
                    db.session.execute(text(sql))
                    print(f"   ✅ Comando {i} executado com sucesso")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"   ⚠️ Comando {i}: Já existe (ignorando)")
                    else:
                        print(f"   ❌ Erro no comando {i}: {e}")
                        raise
            
            # Commit das alterações
            db.session.commit()
            print("\n✅ Todas as alterações foram aplicadas com sucesso!")
            
            # Verificar se as colunas foram criadas
            print("\n🔍 Verificando colunas criadas...")
            
            result = db.session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'separacao' 
                AND column_name IN (
                    'sincronizado_nf', 
                    'numero_nf', 
                    'data_sincronizacao', 
                    'zerado_por_sync', 
                    'data_zeragem'
                )
                ORDER BY column_name
            """))
            
            colunas = result.fetchall()
            
            if colunas:
                print("\n📊 Colunas encontradas na tabela 'separacao':")
                print("-" * 40)
                for coluna, tipo in colunas:
                    print(f"   ✓ {coluna:<20} ({tipo})")
                print("-" * 40)
                
                if len(colunas) == 5:
                    print("\n✅ SUCESSO: Todas as 5 colunas foram criadas!")
                else:
                    print(f"\n⚠️ Foram criadas {len(colunas)} de 5 colunas")
            else:
                print("\n❌ ERRO: Nenhuma coluna foi encontrada!")
                return False
            
            # Verificar índices
            print("\n🔍 Verificando índices criados...")
            result_idx = db.session.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'separacao' 
                AND indexname IN (
                    'idx_separacao_sincronizado_nf',
                    'idx_separacao_numero_nf',
                    'idx_separacao_zerado_por_sync'
                )
            """))
            
            indices = result_idx.fetchall()
            if indices:
                print(f"   ✓ {len(indices)} índices criados")
            
            print("\n" + "=" * 60)
            print("✅ MIGRATIONS APLICADAS COM SUCESSO!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO FATAL: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    sucesso = aplicar_migrations()
    sys.exit(0 if sucesso else 1)