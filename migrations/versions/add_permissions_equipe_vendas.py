"""Adicionar sistema de permissoes avancadas e campo equipe_vendas

Revision ID: add_permissions_equipe_vendas
Revises: 
Create Date: 2025-01-27 16:54:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_permissions_equipe_vendas'
down_revision = 'fix_pre_sep_system'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Adicionar campo equipe_vendas às tabelas existentes
    op.add_column('relatoriofaturamentoimportado', 
                  sa.Column('equipe_vendas', sa.String(100), nullable=True))
    
    op.add_column('faturamentoproduto', 
                  sa.Column('equipe_vendas', sa.String(100), nullable=True))
    
    # 2. Criar tabelas do sistema de permissões
    
    # Tabela perfil_usuario
    op.create_table('perfil_usuario',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nome', sa.String(50), unique=True, nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('nivel_hierarquico', sa.Integer(), default=0, nullable=False),
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.Column('criado_em', sa.DateTime(), default=datetime.utcnow, nullable=False),
        sa.Column('criado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True)
    )
    
    # Tabela modulo_sistema
    op.create_table('modulo_sistema',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('nome', sa.String(50), unique=True, nullable=False),
        sa.Column('nome_exibicao', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('icone', sa.String(50), default='📊', nullable=True),
        sa.Column('cor', sa.String(7), default='#007bff', nullable=True),
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.Column('ordem', sa.Integer(), default=0, nullable=False),
        sa.Column('criado_em', sa.DateTime(), default=datetime.utcnow, nullable=False)
    )
    
    # Tabela funcao_modulo  
    op.create_table('funcao_modulo',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('modulo_id', sa.Integer(), sa.ForeignKey('modulo_sistema.id'), nullable=False),
        sa.Column('nome', sa.String(50), nullable=False),
        sa.Column('nome_exibicao', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('rota_padrao', sa.String(200), nullable=True),
        sa.Column('nivel_critico', sa.String(10), default='NORMAL', nullable=False),
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.Column('ordem', sa.Integer(), default=0, nullable=False),
        sa.Column('criado_em', sa.DateTime(), default=datetime.utcnow, nullable=False),
        sa.UniqueConstraint('modulo_id', 'nome', name='uq_funcao_modulo_nome')
    )
    
    # Tabela permissao_usuario
    op.create_table('permissao_usuario',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('funcao_id', sa.Integer(), sa.ForeignKey('funcao_modulo.id'), nullable=False),
        sa.Column('pode_visualizar', sa.Boolean(), default=False, nullable=False),
        sa.Column('pode_editar', sa.Boolean(), default=False, nullable=False),
        sa.Column('concedida_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('concedida_em', sa.DateTime(), default=datetime.utcnow, nullable=False),
        sa.Column('expira_em', sa.DateTime(), nullable=True),
        sa.Column('observacoes', sa.String(255), nullable=True),
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.UniqueConstraint('usuario_id', 'funcao_id', name='uq_usuario_funcao')
    )
    
    # Tabela usuario_vendedor
    op.create_table('usuario_vendedor',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('vendedor', sa.String(100), nullable=False),
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.Column('adicionado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('adicionado_em', sa.DateTime(), default=datetime.utcnow, nullable=False),
        sa.Column('observacoes', sa.String(255), nullable=True),
        sa.UniqueConstraint('usuario_id', 'vendedor', name='uq_usuario_vendedor')
    )
    
    # Tabela usuario_equipe_vendas
    op.create_table('usuario_equipe_vendas',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('equipe_vendas', sa.String(100), nullable=False),
        sa.Column('ativo', sa.Boolean(), default=True, nullable=False),
        sa.Column('adicionado_por', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('adicionado_em', sa.DateTime(), default=datetime.utcnow, nullable=False),
        sa.Column('observacoes', sa.String(255), nullable=True),
        sa.UniqueConstraint('usuario_id', 'equipe_vendas', name='uq_usuario_equipe')
    )
    
    # Tabela log_permissao
    op.create_table('log_permissao',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('acao', sa.String(50), nullable=False),
        sa.Column('modulo', sa.String(50), nullable=True),
        sa.Column('funcao', sa.String(50), nullable=True),
        sa.Column('usuario_afetado_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
        sa.Column('dados_antes', sa.Text(), nullable=True),
        sa.Column('dados_depois', sa.Text(), nullable=True),
        sa.Column('ip_origem', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('criado_em', sa.DateTime(), default=datetime.utcnow, nullable=False)
    )
    
    # 3. Criar índices para performance
    op.create_index('idx_relatoriofaturamento_equipe_vendas', 'relatoriofaturamentoimportado', ['equipe_vendas'])
    op.create_index('idx_faturamentoproduto_equipe_vendas', 'faturamentoproduto', ['equipe_vendas'])
    
    # Índices das permissões
    op.create_index('idx_permissao_usuario_lookup', 'permissao_usuario', ['usuario_id', 'funcao_id'])
    op.create_index('idx_permissao_usuario_ativo', 'permissao_usuario', ['usuario_id', 'ativo'])
    
    # Índices dos vendedores  
    op.create_index('idx_usuario_vendedor_lookup', 'usuario_vendedor', ['usuario_id', 'vendedor'])
    op.create_index('idx_usuario_vendedor_ativo', 'usuario_vendedor', ['usuario_id', 'ativo'])
    op.create_index('idx_vendedor_lookup', 'usuario_vendedor', ['vendedor', 'ativo'])
    
    # Índices das equipes
    op.create_index('idx_usuario_equipe_lookup', 'usuario_equipe_vendas', ['usuario_id', 'equipe_vendas'])
    op.create_index('idx_usuario_equipe_ativo', 'usuario_equipe_vendas', ['usuario_id', 'ativo'])
    op.create_index('idx_equipe_vendas_lookup', 'usuario_equipe_vendas', ['equipe_vendas', 'ativo'])
    
    # Índices dos módulos/funções
    op.create_index('idx_funcao_modulo_ativo', 'funcao_modulo', ['modulo_id', 'ativo'])
    
    # Índices dos logs
    op.create_index('idx_log_permissao_data', 'log_permissao', ['criado_em'])
    op.create_index('idx_log_permissao_usuario', 'log_permissao', ['usuario_id', 'criado_em'])

def downgrade():
    # Remover índices
    op.drop_index('idx_log_permissao_usuario')
    op.drop_index('idx_log_permissao_data')
    op.drop_index('idx_funcao_modulo_ativo')
    op.drop_index('idx_equipe_vendas_lookup')
    op.drop_index('idx_usuario_equipe_ativo')
    op.drop_index('idx_usuario_equipe_lookup')
    op.drop_index('idx_vendedor_lookup')
    op.drop_index('idx_usuario_vendedor_ativo')
    op.drop_index('idx_usuario_vendedor_lookup')
    op.drop_index('idx_permissao_usuario_ativo')
    op.drop_index('idx_permissao_usuario_lookup')
    op.drop_index('idx_faturamentoproduto_equipe_vendas')
    op.drop_index('idx_relatoriofaturamento_equipe_vendas')
    
    # Remover tabelas do sistema de permissões
    op.drop_table('log_permissao')
    op.drop_table('usuario_equipe_vendas')
    op.drop_table('usuario_vendedor')
    op.drop_table('permissao_usuario')
    op.drop_table('funcao_modulo')
    op.drop_table('modulo_sistema')
    op.drop_table('perfil_usuario')
    
    # Remover campos equipe_vendas
    op.drop_column('faturamentoproduto', 'equipe_vendas')
    op.drop_column('relatoriofaturamentoimportado', 'equipe_vendas') 