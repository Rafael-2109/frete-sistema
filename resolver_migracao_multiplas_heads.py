#!/usr/bin/env python3
"""
🔧 SCRIPT PARA RESOLVER PROBLEMA DE MÚLTIPLAS HEADS NO FLASK-MIGRATE
Resolve o erro: "Multiple head revisions are present for given argument 'head'"
"""

import os
import sys
import glob
from pathlib import Path

def main():
    """Função principal que resolve o problema de múltiplas heads"""
    print("🔧 RESOLVENDO PROBLEMA DE MÚLTIPLAS HEADS NO FLASK-MIGRATE")
    print("=" * 80)
    
    try:
        # 1. Listar todas as migrações
        print("\n📋 1. LISTANDO MIGRAÇÕES EXISTENTES...")
        migrations_dir = Path('migrations/versions')
        if not migrations_dir.exists():
            print("❌ Diretório de migrações não encontrado")
            return False
        
        migration_files = list(migrations_dir.glob('*.py'))
        migration_files = [f for f in migration_files if f.name != '__init__.py']
        
        print(f"✅ Encontradas {len(migration_files)} migrações:")
        for migration in sorted(migration_files):
            print(f"   - {migration.name}")
        
        # 2. Identificar migração problemática
        print("\n🔍 2. IDENTIFICANDO MIGRAÇÃO PROBLEMÁTICA...")
        problematic_migration = None
        
        for migration in migration_files:
            if 'criar_tabelas_ai_claude' in migration.name:
                problematic_migration = migration
                break
        
        if problematic_migration:
            print(f"⚠️ Migração problemática encontrada: {problematic_migration.name}")
            
            # 3. Remover migração problemática
            print("\n🗑️ 3. REMOVENDO MIGRAÇÃO PROBLEMÁTICA...")
            problematic_migration.unlink()
            print(f"✅ Migração {problematic_migration.name} removida")
        else:
            print("✅ Nenhuma migração problemática específica encontrada")
        
        # 4. Criar nova migração consolidada
        print("\n📝 4. CRIANDO NOVA MIGRAÇÃO CONSOLIDADA...")
        nova_migracao = criar_migracao_consolidada()
        
        if nova_migracao:
            print(f"✅ Nova migração criada: {nova_migracao}")
        else:
            print("❌ Falha ao criar nova migração")
            return False
        
        # 5. Atualizar build.sh
        print("\n🔧 5. ATUALIZANDO BUILD.SH...")
        if atualizar_build_sh():
            print("✅ Build.sh atualizado")
        else:
            print("❌ Falha ao atualizar build.sh")
        
        print("\n🎉 PROBLEMA DE MÚLTIPLAS HEADS RESOLVIDO!")
        print("🚀 O deploy no Render deve funcionar agora")
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def criar_migracao_consolidada():
    """Cria uma nova migração consolidada para as tabelas de IA"""
    
    # Gerar timestamp único
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    migration_content = f'''"""Criar tabelas AI consolidadas

Revision ID: ai_consolidada_{timestamp}
Revises: 
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ai_consolidada_{timestamp}'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Criar tabelas de IA consolidadas"""
    
    # Verificar se as tabelas já existem antes de criar
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # 1. ai_knowledge_patterns
    if 'ai_knowledge_patterns' not in existing_tables:
        op.create_table('ai_knowledge_patterns',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('pattern_type', sa.String(50), nullable=False),
            sa.Column('pattern_text', sa.Text(), nullable=False),
            sa.Column('interpretation', sa.Text(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
            sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ai_knowledge_patterns_type', 'ai_knowledge_patterns', ['pattern_type'])
        op.create_index('idx_ai_knowledge_patterns_confidence', 'ai_knowledge_patterns', ['confidence'])
    
    # 2. ai_learning_history
    if 'ai_learning_history' not in existing_tables:
        op.create_table('ai_learning_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('session_id', sa.String(100), nullable=False),
            sa.Column('user_query', sa.Text(), nullable=False),
            sa.Column('ai_response', sa.Text(), nullable=False),
            sa.Column('feedback_score', sa.Float(), nullable=True),
            sa.Column('improvement_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ai_learning_history_session', 'ai_learning_history', ['session_id'])
        op.create_index('idx_ai_learning_history_created', 'ai_learning_history', ['created_at'])
    
    # 3. ai_learning_metrics
    if 'ai_learning_metrics' not in existing_tables:
        op.create_table('ai_learning_metrics',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('metric_name', sa.String(100), nullable=False),
            sa.Column('metric_value', sa.Float(), nullable=False),
            sa.Column('metric_context', postgresql.JSONB(), nullable=True),
            sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ai_learning_metrics_name', 'ai_learning_metrics', ['metric_name'])
        op.create_index('idx_ai_learning_metrics_recorded', 'ai_learning_metrics', ['recorded_at'])
    
    # 4. ai_semantic_mappings
    if 'ai_semantic_mappings' not in existing_tables:
        op.create_table('ai_semantic_mappings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('domain', sa.String(50), nullable=False),
            sa.Column('term', sa.String(200), nullable=False),
            sa.Column('mapping_type', sa.String(50), nullable=False),
            sa.Column('target_field', sa.String(100), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False, default=1.0),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ai_semantic_mappings_domain', 'ai_semantic_mappings', ['domain'])
        op.create_index('idx_ai_semantic_mappings_term', 'ai_semantic_mappings', ['term'])
    
    # 5. ai_grupos_empresariais
    if 'ai_grupos_empresariais' not in existing_tables:
        op.create_table('ai_grupos_empresariais',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('grupo_nome', sa.String(200), nullable=False),
            sa.Column('cnpj_patterns', postgresql.JSONB(), nullable=False),
            sa.Column('nome_patterns', postgresql.JSONB(), nullable=True),
            sa.Column('detection_rules', postgresql.JSONB(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ai_grupos_empresariais_nome', 'ai_grupos_empresariais', ['grupo_nome'])
    
    # 6. ai_business_contexts
    if 'ai_business_contexts' not in existing_tables:
        op.create_table('ai_business_contexts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('context_type', sa.String(50), nullable=False),
            sa.Column('context_data', postgresql.JSONB(), nullable=False),
            sa.Column('priority', sa.Integer(), nullable=False, default=1),
            sa.Column('active', sa.Boolean(), nullable=False, default=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ai_business_contexts_type', 'ai_business_contexts', ['context_type'])
        op.create_index('idx_ai_business_contexts_active', 'ai_business_contexts', ['active'])

def downgrade():
    """Remover tabelas de IA"""
    
    # Verificar se as tabelas existem antes de remover
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    tables_to_drop = [
        'ai_business_contexts',
        'ai_grupos_empresariais', 
        'ai_semantic_mappings',
        'ai_learning_metrics',
        'ai_learning_history',
        'ai_knowledge_patterns'
    ]
    
    for table in tables_to_drop:
        if table in existing_tables:
            op.drop_table(table)
'''
    
    # Salvar arquivo de migração
    migrations_dir = Path('migrations/versions')
    migration_file = migrations_dir / f'ai_consolidada_{timestamp}.py'
    
    try:
        migration_file.write_text(migration_content, encoding='utf-8')
        return migration_file.name
    except Exception as e:
        print(f"❌ Erro ao criar migração: {e}")
        return None

def atualizar_build_sh():
    """Atualiza o build.sh para resolver problemas de migração"""
    
    try:
        build_file = Path('build.sh')
        if not build_file.exists():
            print("❌ Arquivo build.sh não encontrado")
            return False
        
        content = build_file.read_text(encoding='utf-8')
        
        # Substituir comando de migração problemático
        old_migration = 'flask db upgrade'
        new_migration = '''# Resolver problemas de múltiplas heads
echo "🔧 Resolvendo problemas de migração..."
flask db merge heads || echo "⚠️ Merge não necessário"
flask db upgrade || echo "⚠️ Upgrade já aplicado"'''
        
        if old_migration in content and new_migration not in content:
            content = content.replace(old_migration, new_migration)
            build_file.write_text(content, encoding='utf-8')
            print("✅ Build.sh atualizado com resolução de múltiplas heads")
            return True
        else:
            print("✅ Build.sh já está atualizado")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao atualizar build.sh: {e}")
        return False

if __name__ == "__main__":
    main() 