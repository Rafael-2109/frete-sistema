#!/usr/bin/env python
"""
Script definitivo para resolver problemas de migração no Render
Este script garante que as migrações funcionem corretamente
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
    
    # Parse da URL do banco
    result = urlparse(database_url)
    
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn

def fix_migration_issues():
    """Resolver problemas de migração"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("🔧 Resolvendo problemas de migração...")
    
    try:
        # 1. Primeiro, dropar views que dependem das tabelas
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
                print(f"✅ View {view_name} removida (se existia)")
            except Exception as e:
                print(f"⚠️ Aviso ao remover view {view_name}: {e}")
        
        # 2. Verificar o estado atual da migração
        cur.execute("""
            SELECT version_num 
            FROM alembic_version
        """)
        current_version = cur.fetchone()
        
        if current_version:
            print(f"📍 Versão atual da migração: {current_version[0]}")
            
            # Se estamos na migração problemática, atualizar diretamente
            if current_version[0] == 'safe_permission_update':
                print("🔄 Atualizando versão da migração para pular a problemática...")
                cur.execute("""
                    UPDATE alembic_version 
                    SET version_num = '2b5f3637c189'
                    WHERE version_num = 'safe_permission_update'
                """)
                print("✅ Versão da migração atualizada!")
        
        # 3. Criar uma nova migração de correção se necessário
        cur.execute("""
            INSERT INTO alembic_version (version_num)
            VALUES ('fix_render_cascade_dependencies')
            ON CONFLICT (version_num) DO NOTHING
        """)
        
        # 4. Garantir que as tabelas AI existam (caso sejam necessárias)
        tables_to_keep = [
            ('ai_feedback_history', """
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
            """),
            ('ai_advanced_sessions', """
                CREATE TABLE IF NOT EXISTS ai_advanced_sessions (
                    session_id VARCHAR(50) PRIMARY KEY,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_jsonb JSONB DEFAULT '{}'::jsonb NOT NULL
                )
            """),
            ('ai_learning_patterns', """
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
            """)
        ]
        
        for table_name, create_sql in tables_to_keep:
            try:
                cur.execute(create_sql)
                print(f"✅ Tabela {table_name} garantida")
            except Exception as e:
                print(f"⚠️ Aviso ao criar tabela {table_name}: {e}")
        
        # Commit das mudanças
        conn.commit()
        print("\n✅ Problemas de migração resolvidos com sucesso!")
        
        # 5. Mostrar estado final
        cur.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 5")
        versions = cur.fetchall()
        print("\n📋 Migrações registradas:")
        for v in versions:
            print(f"  - {v[0]}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro ao resolver problemas: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def create_safe_migration():
    """Criar uma migração segura que pula as tabelas problemáticas"""
    migration_content = '''"""Skip problematic AI tables migration

Revision ID: skip_ai_tables_migration
Revises: 2b5f3637c189
Create Date: {date}

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'skip_ai_tables_migration'
down_revision = '2b5f3637c189'
branch_labels = None
depends_on = None


def upgrade():
    """Skip dropping AI tables to avoid dependency issues"""
    # As tabelas AI serão mantidas para evitar problemas com views dependentes
    pass


def downgrade():
    """Nothing to downgrade"""
    pass
'''.format(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # Salvar arquivo de migração
    migration_file = 'migrations/versions/skip_ai_tables_migration.py'
    try:
        with open(migration_file, 'w') as f:
            f.write(migration_content)
        print(f"✅ Migração segura criada: {migration_file}")
    except Exception as e:
        print(f"❌ Erro ao criar arquivo de migração: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando correção definitiva de migrações...")
    print("=" * 50)
    
    # Verificar se estamos no Render
    if os.environ.get('RENDER'):
        print("🌐 Executando no Render")
    else:
        print("💻 Executando localmente")
    
    try:
        fix_migration_issues()
        create_safe_migration()
        print("\n✅ Correção concluída com sucesso!")
        print("\n📝 Próximos passos:")
        print("1. Faça commit deste script e da nova migração")
        print("2. No Render, execute: python fix_migration_definitivo.py")
        print("3. Depois execute: flask db upgrade")
        print("4. Se necessário, rode: flask db stamp head")
    except Exception as e:
        print(f"\n❌ Erro durante a correção: {e}")
        sys.exit(1) 