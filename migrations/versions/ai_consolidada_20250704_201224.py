"""Criar tabelas AI consolidadas

Revision ID: ai_consolidada_20250704_201224
Revises: 
Create Date: 2025-07-04T20:12:24.175014

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ai_consolidada_20250704_201224'
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
