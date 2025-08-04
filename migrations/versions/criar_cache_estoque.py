"""Criar tabelas de cache para saldo de estoque

Revision ID: criar_cache_estoque
Revises: 
Create Date: 2025-08-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'criar_cache_estoque'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela de cache do saldo de estoque
    op.create_table('saldo_estoque_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cod_produto', sa.String(50), nullable=False),
        sa.Column('nome_produto', sa.String(200), nullable=False),
        
        # Saldo atual (soma de todas as movimentações)
        sa.Column('saldo_atual', sa.Numeric(15, 3), nullable=False, default=0),
        
        # Quantidades em carteira/separação (para cálculo rápido)
        sa.Column('qtd_carteira', sa.Numeric(15, 3), nullable=False, default=0),
        sa.Column('qtd_pre_separacao', sa.Numeric(15, 3), nullable=False, default=0),
        sa.Column('qtd_separacao', sa.Numeric(15, 3), nullable=False, default=0),
        
        # Estatísticas pré-calculadas
        sa.Column('previsao_ruptura_7d', sa.Numeric(15, 3), nullable=True),
        sa.Column('status_ruptura', sa.String(20), nullable=True),
        
        # Controle de atualização
        sa.Column('ultima_atualizacao_saldo', sa.DateTime(), nullable=True),
        sa.Column('ultima_atualizacao_carteira', sa.DateTime(), nullable=True),
        sa.Column('ultima_atualizacao_projecao', sa.DateTime(), nullable=True),
        
        # Auditoria
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Índices para performance
    op.create_index('idx_saldo_cache_cod_produto', 'saldo_estoque_cache', ['cod_produto'], unique=True)
    op.create_index('idx_saldo_cache_status', 'saldo_estoque_cache', ['status_ruptura'])
    op.create_index('idx_saldo_cache_ruptura', 'saldo_estoque_cache', ['previsao_ruptura_7d'])
    
    # Criar tabela de projeção de estoque (29 dias)
    op.create_table('projecao_estoque_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cod_produto', sa.String(50), nullable=False),
        sa.Column('data_projecao', sa.Date(), nullable=False),
        sa.Column('dia_offset', sa.Integer(), nullable=False),  # 0 = D0, 1 = D+1, etc
        
        # Valores da projeção
        sa.Column('estoque_inicial', sa.Numeric(15, 3), nullable=False, default=0),
        sa.Column('saida_prevista', sa.Numeric(15, 3), nullable=False, default=0),
        sa.Column('producao_programada', sa.Numeric(15, 3), nullable=False, default=0),
        sa.Column('estoque_final', sa.Numeric(15, 3), nullable=False, default=0),
        
        # Controle
        sa.Column('atualizado_em', sa.DateTime(), nullable=False),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Índices compostos para busca rápida
    op.create_index('idx_projecao_produto_data', 'projecao_estoque_cache', ['cod_produto', 'data_projecao'], unique=True)
    op.create_index('idx_projecao_produto_dia', 'projecao_estoque_cache', ['cod_produto', 'dia_offset'])
    
    # Criar tabela de controle de atualização
    op.create_table('cache_update_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tabela_origem', sa.String(50), nullable=False),
        sa.Column('operacao', sa.String(20), nullable=False),  # INSERT, UPDATE, DELETE
        sa.Column('cod_produto', sa.String(50), nullable=True),
        sa.Column('processado', sa.Boolean(), default=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('processado_em', sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_cache_log_processado', 'cache_update_log', ['processado'])
    op.create_index('idx_cache_log_produto', 'cache_update_log', ['cod_produto'])


def downgrade():
    op.drop_index('idx_cache_log_produto', table_name='cache_update_log')
    op.drop_index('idx_cache_log_processado', table_name='cache_update_log')
    op.drop_table('cache_update_log')
    
    op.drop_index('idx_projecao_produto_dia', table_name='projecao_estoque_cache')
    op.drop_index('idx_projecao_produto_data', table_name='projecao_estoque_cache')
    op.drop_table('projecao_estoque_cache')
    
    op.drop_index('idx_saldo_cache_ruptura', table_name='saldo_estoque_cache')
    op.drop_index('idx_saldo_cache_status', table_name='saldo_estoque_cache')
    op.drop_index('idx_saldo_cache_cod_produto', table_name='saldo_estoque_cache')
    op.drop_table('saldo_estoque_cache')