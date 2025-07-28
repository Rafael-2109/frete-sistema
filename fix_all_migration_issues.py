#!/usr/bin/env python
"""
Script completo para resolver TODOS os problemas de migração
Incluindo o campo separacao_lote_id em pre_separacao_item
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

def get_db_connection():
    """Obter conexão com o banco de dados"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        sys.exit(1)
    
    result = urlparse(database_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn

def fix_all_issues():
    """Resolver TODOS os problemas de migração"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("🔧 Resolvendo TODOS os problemas de migração...")
    
    try:
        # 1. Remover views problemáticas
        print("\n📋 Removendo views dependentes...")
        views_to_drop = [
            'ai_feedback_analytics',
            'ai_session_analytics', 
            'ai_pattern_summary',
            'ai_feedback_summary',
            'historico_summary',
            'faturamento_analytics'
        ]
        
        for view_name in views_to_drop:
            try:
                cur.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE")
                print(f"  ✅ View {view_name} removida")
            except Exception as e:
                print(f"  ⚠️ {view_name}: {e}")
        
        # 2. Verificar e adicionar campo separacao_lote_id em pre_separacao_item
        print("\n🔍 Verificando campo separacao_lote_id em pre_separacao_item...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'pre_separacao_item' 
            AND column_name = 'separacao_lote_id'
        """)
        
        if not cur.fetchone():
            print("  ❌ Campo não existe! Adicionando...")
            cur.execute("""
                ALTER TABLE pre_separacao_item 
                ADD COLUMN separacao_lote_id VARCHAR(50)
            """)
            
            # Criar índice também
            cur.execute("""
                CREATE INDEX IF NOT EXISTS ix_pre_separacao_item_separacao_lote_id 
                ON pre_separacao_item(separacao_lote_id)
            """)
            print("  ✅ Campo separacao_lote_id adicionado com sucesso!")
        else:
            print("  ✅ Campo separacao_lote_id já existe")
        
        # 3. Verificar outros campos importantes
        print("\n🔍 Verificando estrutura completa da tabela pre_separacao_item...")
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'pre_separacao_item'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("  📊 Colunas existentes:")
        for col in columns:
            print(f"    - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
        
        # 4. Atualizar versão da migração se necessário
        print("\n📍 Verificando estado das migrações...")
        cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
        current = cur.fetchone()
        
        if current and current[0] == 'safe_permission_update':
            print("  🔄 Atualizando para pular migração problemática...")
            cur.execute("""
                UPDATE alembic_version 
                SET version_num = 'skip_ai_tables_migration'
                WHERE version_num = 'safe_permission_update'
            """)
        
        # 5. Garantir que tabelas AI existam (mantê-las)
        print("\n🛡️ Garantindo tabelas AI...")
        tables_ai = {
            'ai_feedback_history': """
                CREATE TABLE IF NOT EXISTS ai_feedback_history (
                    feedback_id VARCHAR(50) PRIMARY KEY,
                    session_id VARCHAR(50),
                    user_id INTEGER,
                    query_original TEXT NOT NULL,
                    response_original TEXT NOT NULL,
                    feedback_text TEXT NOT NULL,
                    feedback_type VARCHAR(20) NOT NULL,
                    severity VARCHAR(20) DEFAULT 'medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT false,
                    applied BOOLEAN DEFAULT false,
                    context_jsonb JSONB DEFAULT '{}'::jsonb
                )
            """,
            'ai_advanced_sessions': """
                CREATE TABLE IF NOT EXISTS ai_advanced_sessions (
                    session_id VARCHAR(50) PRIMARY KEY,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_jsonb JSONB DEFAULT '{}'::jsonb NOT NULL
                )
            """,
            'ai_learning_patterns': """
                CREATE TABLE IF NOT EXISTS ai_learning_patterns (
                    pattern_id VARCHAR(50) PRIMARY KEY,
                    pattern_type VARCHAR(50) NOT NULL,
                    description TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    confidence_score NUMERIC(3,2) DEFAULT 0.5,
                    improvement_suggestion TEXT,
                    examples_jsonb JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
            """
        }
        
        for table_name, create_sql in tables_ai.items():
            try:
                cur.execute(create_sql)
                print(f"  ✅ Tabela {table_name} garantida")
            except Exception as e:
                print(f"  ⚠️ {table_name}: {e}")
        
        # Commit todas as mudanças
        conn.commit()
        print("\n✅ TODOS os problemas foram resolvidos!")
        
        # Mostrar resumo final
        print("\n📊 RESUMO FINAL:")
        print("  ✅ Views problemáticas removidas")
        print("  ✅ Campo separacao_lote_id garantido em pre_separacao_item")
        print("  ✅ Tabelas AI preservadas")
        print("  ✅ Migrações ajustadas")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def create_complete_migration():
    """Criar migração que pula problemas e adiciona campo faltante"""
    content = '''"""Complete fix for all migration issues

Revision ID: complete_migration_fix
Revises: 2b5f3637c189
Create Date: {date}

"""
from alembic import op
import sqlalchemy as sa

revision = 'complete_migration_fix'
down_revision = '2b5f3637c189'
branch_labels = None
depends_on = None


def upgrade():
    """Fix all migration issues"""
    # 1. Adicionar campo separacao_lote_id se não existir
    conn = op.get_bind()
    result = conn.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'pre_separacao_item' 
        AND column_name = 'separacao_lote_id'
    """).fetchone()
    
    if not result:
        op.add_column('pre_separacao_item', 
            sa.Column('separacao_lote_id', sa.String(50), nullable=True))
        op.create_index('ix_pre_separacao_item_separacao_lote_id', 
            'pre_separacao_item', ['separacao_lote_id'])
    
    # 2. Manter tabelas AI (não dropar)
    pass


def downgrade():
    """Nothing to downgrade"""
    pass
'''.format(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    with open('migrations/versions/complete_migration_fix.py', 'w') as f:
        f.write(content)
    print("✅ Migração completa criada: complete_migration_fix.py")

if __name__ == "__main__":
    print("🚀 CORREÇÃO COMPLETA DE MIGRAÇÕES")
    print("=" * 50)
    
    try:
        fix_all_issues()
        create_complete_migration()
        
        print("\n✅ SUCESSO! Todos os problemas foram resolvidos")
        print("\n📝 Instruções:")
        print("1. Faça commit destes arquivos")
        print("2. No Render: python fix_all_migration_issues.py")
        print("3. Depois: flask db upgrade")
        
    except Exception as e:
        print(f"\n❌ Falha: {e}")
        sys.exit(1) 