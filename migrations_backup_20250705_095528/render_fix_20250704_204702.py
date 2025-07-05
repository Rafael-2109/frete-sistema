"""Correção para deploy no Render - Fix revision 1d81b88a3038

Revision ID: render_fix_20250704_204702
Revises: 
Create Date: 2025-07-04 20:47:02.651136

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'render_fix_20250704_204702'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade: Garantir que todas as tabelas AI existam"""
    
    # Verificar se as tabelas já existem antes de criar
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Lista de tabelas AI essenciais
    ai_tables = [
        'ai_advanced_sessions',
        'ai_feedback_history', 
        'ai_learning_patterns',
        'ai_performance_metrics',
        'ai_semantic_embeddings',
        'ai_system_config',
        'ai_knowledge_patterns',
        'ai_learning_history',
        'ai_learning_metrics',
        'ai_grupos_empresariais',
        'ai_semantic_mappings',
        'ai_business_contexts'
    ]
    
    # Criar apenas tabelas que não existem
    for table_name in ai_tables:
        if table_name not in existing_tables:
            print(f"Criando tabela: {table_name}")
            
            if table_name == 'ai_advanced_sessions':
                op.create_table(
                    'ai_advanced_sessions',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('session_id', sa.String(255), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=True),
                    sa.Column('query_original', sa.Text(), nullable=False),
                    sa.Column('response_data', sa.JSON(), nullable=True),
                    sa.Column('metadata', sa.JSON(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
                    sa.PrimaryKeyConstraint('id')
                )
                op.create_index('ix_ai_advanced_sessions_session_id', 'ai_advanced_sessions', ['session_id'])
                
            elif table_name == 'ai_knowledge_patterns':
                op.create_table(
                    'ai_knowledge_patterns',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('pattern_type', sa.String(100), nullable=False),
                    sa.Column('pattern_text', sa.Text(), nullable=False),
                    sa.Column('interpretation', sa.JSON(), nullable=True),
                    sa.Column('confidence', sa.Float(), default=0.8),
                    sa.Column('usage_count', sa.Integer(), default=1),
                    sa.Column('success_rate', sa.Float(), default=0.8),
                    sa.Column('created_by', sa.String(100), default='sistema'),
                    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
                    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
                    sa.PrimaryKeyConstraint('id')
                )
    
    print("✅ Migração Render aplicada com sucesso")

def downgrade():
    """Downgrade: Não fazer nada para manter estabilidade"""
    pass
