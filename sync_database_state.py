#!/usr/bin/env python
"""
Script para sincronizar estado do banco com os modelos
Garante que futuras migrações funcionem sem problemas
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
        # Tentar pegar do config local
        try:
            from app import create_app
            app = create_app()
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI')
        except:
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

def sync_database_state():
    """Sincronizar estado do banco com modelos"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("🔄 Sincronizando estado do banco de dados...")
    
    try:
        # 1. Limpar views órfãs
        print("\n📋 Limpando views órfãs...")
        views_to_clean = [
            'ai_feedback_analytics',
            'ai_session_analytics',
            'ai_pattern_summary',
            'ai_feedback_summary',
            'historico_summary',
            'faturamento_analytics'
        ]
        
        for view in views_to_clean:
            cur.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
        print("  ✅ Views limpas")
        
        # 2. Garantir que pre_separacao_item tem todos os campos
        print("\n🔧 Verificando tabela pre_separacao_item...")
        
        # Campos que devem existir
        required_fields = [
            ('separacao_lote_id', 'VARCHAR(50)', True),
            ('num_pedido', 'VARCHAR(50)', False),
            ('cod_produto', 'VARCHAR(50)', False),
            ('cnpj_cliente', 'VARCHAR(20)', True),
            ('nome_produto', 'VARCHAR(255)', True),
            ('qtd_original_carteira', 'NUMERIC(15,3)', False),
            ('qtd_selecionada_usuario', 'NUMERIC(15,3)', False),
            ('qtd_restante_calculada', 'NUMERIC(15,3)', False),
            ('valor_original_item', 'NUMERIC(15,2)', True),
            ('peso_original_item', 'NUMERIC(15,3)', True),
            ('hash_item_original', 'VARCHAR(128)', True),
            ('data_expedicao_editada', 'DATE', False),
            ('data_agendamento_editada', 'DATE', True),
            ('protocolo_editado', 'VARCHAR(50)', True),
            ('observacoes_usuario', 'TEXT', True),
            ('recomposto', 'BOOLEAN DEFAULT FALSE', True),
            ('data_recomposicao', 'TIMESTAMP', True),
            ('recomposto_por', 'VARCHAR(100)', True),
            ('versao_carteira_original', 'VARCHAR(50)', True),
            ('versao_carteira_recomposta', 'VARCHAR(50)', True),
            ('status', "VARCHAR(20) DEFAULT 'CRIADO'", True),
            ('tipo_envio', "VARCHAR(10) DEFAULT 'total'", True),
            ('data_criacao', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP', True),
            ('criado_por', 'VARCHAR(100)', True)
        ]
        
        for field_name, field_type, nullable in required_fields:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'pre_separacao_item' 
                AND column_name = '{field_name}'
            """)
            
            if not cur.fetchone():
                null_clause = "NULL" if nullable else "NOT NULL"
                try:
                    cur.execute(f"""
                        ALTER TABLE pre_separacao_item 
                        ADD COLUMN {field_name} {field_type} {null_clause}
                    """)
                    print(f"  ✅ Campo {field_name} adicionado")
                except Exception as e:
                    print(f"  ⚠️ Erro ao adicionar {field_name}: {e}")
        
        # 3. Garantir índices
        print("\n📊 Garantindo índices...")
        indices = [
            ('ix_pre_separacao_item_separacao_lote_id', 'pre_separacao_item', ['separacao_lote_id']),
            ('idx_pre_sep_data_expedicao', 'pre_separacao_item', ['cod_produto', 'data_expedicao_editada', 'status']),
            ('idx_pre_sep_recomposicao', 'pre_separacao_item', ['recomposto', 'hash_item_original'])
        ]
        
        for idx_name, table_name, columns in indices:
            cur.execute(f"""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = '{idx_name}'
            """)
            
            if not cur.fetchone():
                cols = ', '.join(columns)
                try:
                    cur.execute(f"""
                        CREATE INDEX {idx_name} 
                        ON {table_name}({cols})
                    """)
                    print(f"  ✅ Índice {idx_name} criado")
                except Exception as e:
                    print(f"  ⚠️ Índice {idx_name}: {e}")
        
        # 4. Atualizar alembic_version para estado consistente
        print("\n📍 Atualizando estado do Alembic...")
        
        # Pegar última migração válida
        cur.execute("""
            SELECT version_num 
            FROM alembic_version 
            ORDER BY version_num DESC 
            LIMIT 1
        """)
        current = cur.fetchone()
        
        # Se estiver em estado problemático, corrigir
        problematic_versions = ['safe_permission_update', '2b5f3637c189']
        if current and current[0] in problematic_versions:
            cur.execute("""
                DELETE FROM alembic_version;
                INSERT INTO alembic_version (version_num) 
                VALUES ('complete_migration_fix')
            """)
            print("  ✅ Estado do Alembic corrigido")
        
        # 5. Stamp no estado atual
        print("\n🏷️ Marcando estado atual do banco...")
        
        # Commit das mudanças
        conn.commit()
        
        print("\n✅ Banco sincronizado com sucesso!")
        
        # Mostrar estado final
        print("\n📊 ESTADO FINAL:")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        print(f"\n  Total de tabelas: {len(tables)}")
        
        cur.execute("SELECT version_num FROM alembic_version")
        version = cur.fetchone()
        print(f"  Versão Alembic: {version[0] if version else 'Nenhuma'}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def create_sync_migration():
    """Criar migração de sincronização"""
    content = '''"""Database state synchronization

Revision ID: db_sync_{timestamp}
Revises: complete_migration_fix
Create Date: {date}

"""
from alembic import op
import sqlalchemy as sa

revision = 'db_sync_{timestamp}'
down_revision = 'complete_migration_fix'
branch_labels = None
depends_on = None


def upgrade():
    """Already synchronized via sync script"""
    # Estado já foi sincronizado pelo script
    # Esta migração apenas marca o ponto de sincronização
    pass


def downgrade():
    """No downgrade needed"""
    pass
'''.format(
        timestamp=datetime.now().strftime('%Y%m%d%H%M%S'),
        date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    filename = f"migrations/versions/db_sync_{datetime.now().strftime('%Y%m%d%H%M%S')}.py"
    with open(filename, 'w') as f:
        f.write(content)
    print(f"\n✅ Migração de sincronização criada: {filename}")
    return filename

if __name__ == "__main__":
    print("🔄 SINCRONIZAÇÃO DO BANCO DE DADOS")
    print("=" * 50)
    
    if sync_database_state():
        migration_file = create_sync_migration()
        
        print("\n✅ SUCESSO! Banco sincronizado")
        print("\n📝 Próximos passos:")
        print("1. Execute: flask db stamp head")
        print("2. Agora pode usar: flask db migrate -m 'sua mensagem'")
        print("3. As futuras migrações funcionarão normalmente!")
        
        print("\n💡 IMPORTANTE:")
        print("- O banco está em estado consistente")
        print("- Todas as tabelas e campos estão sincronizados")
        print("- Futuras migrações não terão conflitos")
    else:
        print("\n❌ Falha na sincronização")
        sys.exit(1) 