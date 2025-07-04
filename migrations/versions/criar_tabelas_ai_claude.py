"""Criar tabelas de IA para Claude AI

Revision ID: ai_tables_claude_2025
Revises: 
Create Date: 2025-07-04 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ai_tables_claude_2025'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Criar tabelas de IA para Claude AI"""
    
    # 1. Tabela ai_knowledge_patterns
    op.create_table('ai_knowledge_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('pattern_text', sa.Text(), nullable=False),
        sa.Column('interpretation', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('success_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. Tabela ai_learning_history
    op.create_table('ai_learning_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('consulta_original', sa.Text(), nullable=False),
        sa.Column('interpretacao_inicial', sa.Text(), nullable=True),
        sa.Column('resposta_inicial', sa.Text(), nullable=True),
        sa.Column('feedback_usuario', sa.Text(), nullable=True),
        sa.Column('aprendizado_extraido', sa.Text(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 3. Tabela ai_learning_metrics
    op.create_table('ai_learning_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metrica_tipo', sa.String(50), nullable=False),
        sa.Column('metrica_valor', sa.Float(), nullable=False),
        sa.Column('contexto', sa.Text(), nullable=True),
        sa.Column('periodo_inicio', sa.DateTime(), nullable=False),
        sa.Column('periodo_fim', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 4. Tabela ai_semantic_mappings
    op.create_table('ai_semantic_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('termo_original', sa.String(200), nullable=False),
        sa.Column('termo_normalizado', sa.String(200), nullable=False),
        sa.Column('categoria', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 5. Tabela ai_grupos_empresariais
    op.create_table('ai_grupos_empresariais',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grupo_nome', sa.String(200), nullable=False),
        sa.Column('empresa_nome', sa.String(200), nullable=False),
        sa.Column('cnpj_pattern', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('auto_detected', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 6. Tabela ai_business_contexts
    op.create_table('ai_business_contexts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contexto_tipo', sa.String(50), nullable=False),
        sa.Column('contexto_dados', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 7. Tabela ai_response_templates
    op.create_table('ai_response_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_name', sa.String(100), nullable=False),
        sa.Column('template_content', sa.Text(), nullable=False),
        sa.Column('categoria', sa.String(50), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar índices para performance
    op.create_index('idx_ai_knowledge_patterns_type', 'ai_knowledge_patterns', ['pattern_type'])
    op.create_index('idx_ai_knowledge_patterns_confidence', 'ai_knowledge_patterns', ['confidence'])
    op.create_index('idx_ai_learning_history_usuario', 'ai_learning_history', ['usuario_id'])
    op.create_index('idx_ai_learning_metrics_tipo', 'ai_learning_metrics', ['metrica_tipo'])
    op.create_index('idx_ai_semantic_mappings_categoria', 'ai_semantic_mappings', ['categoria'])
    op.create_index('idx_ai_grupos_empresariais_grupo', 'ai_grupos_empresariais', ['grupo_nome'])
    op.create_index('idx_ai_business_contexts_tipo', 'ai_business_contexts', ['contexto_tipo'])
    op.create_index('idx_ai_response_templates_categoria', 'ai_response_templates', ['categoria'])


def downgrade():
    """Remover tabelas de IA"""
    
    # Remover índices
    op.drop_index('idx_ai_response_templates_categoria')
    op.drop_index('idx_ai_business_contexts_tipo')
    op.drop_index('idx_ai_grupos_empresariais_grupo')
    op.drop_index('idx_ai_semantic_mappings_categoria')
    op.drop_index('idx_ai_learning_metrics_tipo')
    op.drop_index('idx_ai_learning_history_usuario')
    op.drop_index('idx_ai_knowledge_patterns_confidence')
    op.drop_index('idx_ai_knowledge_patterns_type')
    
    # Remover tabelas
    op.drop_table('ai_response_templates')
    op.drop_table('ai_business_contexts')
    op.drop_table('ai_grupos_empresariais')
    op.drop_table('ai_semantic_mappings')
    op.drop_table('ai_learning_metrics')
    op.drop_table('ai_learning_history')
    op.drop_table('ai_knowledge_patterns') 