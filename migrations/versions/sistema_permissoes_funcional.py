"""Sistema unificado de permissões funcional

Revision ID: sistema_permissoes_funcional
Revises: unify_permission_system
Create Date: 2025-01-29 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'sistema_permissoes_funcional'
down_revision = 'unify_permission_system'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabelas de categorias, módulos e submódulos
    op.create_table('permission_category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(50), nullable=False),
        sa.Column('nome_exibicao', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('icone', sa.String(50), nullable=True, server_default='folder'),
        sa.Column('cor', sa.String(7), nullable=True, server_default='#007bff'),
        sa.Column('ordem', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome'),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], )
    )
    
    op.create_table('permission_module',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(50), nullable=False),
        sa.Column('nome_exibicao', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('icone', sa.String(50), nullable=True, server_default='file'),
        sa.Column('cor', sa.String(7), nullable=True, server_default='#6c757d'),
        sa.Column('ordem', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['category_id'], ['permission_category.id'], ),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.UniqueConstraint('category_id', 'nome', name='uq_module_category_name')
    )
    op.create_index('idx_module_category', 'permission_module', ['category_id', 'ativo'])
    
    op.create_table('permission_submodule',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(50), nullable=False),
        sa.Column('nome_exibicao', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('route_pattern', sa.String(200), nullable=True),
        sa.Column('critical_level', sa.String(10), nullable=True, server_default='NORMAL'),
        sa.Column('ordem', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['module_id'], ['permission_module.id'], ),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.UniqueConstraint('module_id', 'nome', name='uq_submodule_module_name'),
        sa.CheckConstraint("critical_level IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')", name='ck_critical_level')
    )
    op.create_index('idx_submodule_module', 'permission_submodule', ['module_id', 'ativo'])
    
    # Criar tabela de permissões de usuário simplificada
    op.create_table('user_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('submodule_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['submodule_id'], ['permission_submodule.id'], ),
        sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id'], ),
        sa.UniqueConstraint('user_id', 'submodule_id', name='uq_user_submodule_permission')
    )
    op.create_index('idx_user_permission_active', 'user_permission', ['user_id', 'ativo'])
    op.create_index('idx_submodule_permission', 'user_permission', ['submodule_id', 'ativo'])
    
    # Criar tabelas de vendedor e equipe
    op.create_table('vendedor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(50), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('email', sa.String(120), nullable=True),
        sa.Column('telefone', sa.String(20), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo'),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], )
    )
    
    op.create_table('equipe_vendas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(50), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('gerente_id', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo'),
        sa.ForeignKeyConstraint(['gerente_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], )
    )
    
    # Criar tabelas de vínculo usuário-vendedor e usuário-equipe
    op.create_table('user_vendedor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vendedor_id', sa.Integer(), nullable=False),
        sa.Column('tipo_acesso', sa.String(20), nullable=True, server_default='view'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('adicionado_por', sa.Integer(), nullable=True),
        sa.Column('adicionado_em', sa.DateTime(), nullable=False),
        sa.Column('observacoes', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['vendedor_id'], ['vendedor.id'], ),
        sa.ForeignKeyConstraint(['adicionado_por'], ['usuarios.id'], ),
        sa.UniqueConstraint('user_id', 'vendedor_id', name='uq_user_vendedor')
    )
    op.create_index('idx_user_vendedor_active', 'user_vendedor', ['user_id', 'ativo'])
    
    op.create_table('user_equipe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('equipe_id', sa.Integer(), nullable=False),
        sa.Column('cargo_equipe', sa.String(50), nullable=True),
        sa.Column('tipo_acesso', sa.String(20), nullable=True, server_default='member'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('adicionado_por', sa.Integer(), nullable=True),
        sa.Column('adicionado_em', sa.DateTime(), nullable=False),
        sa.Column('observacoes', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['equipe_id'], ['equipe_vendas.id'], ),
        sa.ForeignKeyConstraint(['adicionado_por'], ['usuarios.id'], ),
        sa.UniqueConstraint('user_id', 'equipe_id', name='uq_user_equipe')
    )
    op.create_index('idx_user_equipe_active', 'user_equipe', ['user_id', 'ativo'])
    
    # Criar tabelas de permissões por vendedor/equipe
    op.create_table('vendedor_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendedor_id', sa.Integer(), nullable=False),
        sa.Column('submodule_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vendedor_id'], ['vendedor.id'], ),
        sa.ForeignKeyConstraint(['submodule_id'], ['permission_submodule.id'], ),
        sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id'], ),
        sa.UniqueConstraint('vendedor_id', 'submodule_id', name='uq_vendedor_submodule')
    )
    op.create_index('idx_vendedor_permission', 'vendedor_permission', ['vendedor_id', 'ativo'])
    
    op.create_table('equipe_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipe_id', sa.Integer(), nullable=False),
        sa.Column('submodule_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['equipe_id'], ['equipe_vendas.id'], ),
        sa.ForeignKeyConstraint(['submodule_id'], ['permission_submodule.id'], ),
        sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id'], ),
        sa.UniqueConstraint('equipe_id', 'submodule_id', name='uq_equipe_submodule')
    )
    op.create_index('idx_equipe_permission', 'equipe_permission', ['equipe_id', 'ativo'])
    
    # Criar tabela de perfil de usuário
    op.create_table('perfil_usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(50), nullable=False),
        sa.Column('nome_exibicao', sa.String(100), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('nivel_hierarquico', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome'),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], )
    )
    
    # Criar tabela de log de permissões
    op.create_table('permission_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(20), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', sa.String(20), nullable=True, server_default='SUCCESS'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], )
    )
    op.create_index('idx_log_user_timestamp', 'permission_log', ['user_id', 'timestamp'])
    op.create_index('idx_log_action_timestamp', 'permission_log', ['action', 'timestamp'])
    op.create_index('idx_log_result', 'permission_log', ['result', 'timestamp'])
    
    # Criar tabelas auxiliares simplificadas
    op.create_table('permission_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('codigo', sa.String(50), nullable=False),
        sa.Column('descricao', sa.String(255), nullable=True),
        sa.Column('categoria', sa.String(50), nullable=True, server_default='custom'),
        sa.Column('template_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo'),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], )
    )
    
    op.create_table('batch_operation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.String(20), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('executed_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='PENDING'),
        sa.Column('affected_users', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('affected_permissions', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['executed_by'], ['usuarios.id'], )
    )
    
    op.create_table('permission_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('permission_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key'),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], )
    )
    op.create_index('idx_cache_user', 'permission_cache', ['user_id'])
    op.create_index('idx_cache_expires', 'permission_cache', ['expires_at'])


def downgrade():
    # Dropar todas as tabelas na ordem reversa
    op.drop_index('idx_cache_expires', 'permission_cache')
    op.drop_index('idx_cache_user', 'permission_cache')
    op.drop_table('permission_cache')
    op.drop_table('batch_operation')
    op.drop_table('permission_template')
    op.drop_index('idx_log_result', 'permission_log')
    op.drop_index('idx_log_action_timestamp', 'permission_log')
    op.drop_index('idx_log_user_timestamp', 'permission_log')
    op.drop_table('permission_log')
    op.drop_table('perfil_usuario')
    op.drop_index('idx_equipe_permission', 'equipe_permission')
    op.drop_table('equipe_permission')
    op.drop_index('idx_vendedor_permission', 'vendedor_permission')
    op.drop_table('vendedor_permission')
    op.drop_index('idx_user_equipe_active', 'user_equipe')
    op.drop_table('user_equipe')
    op.drop_index('idx_user_vendedor_active', 'user_vendedor')
    op.drop_table('user_vendedor')
    op.drop_table('equipe_vendas')
    op.drop_table('vendedor')
    op.drop_index('idx_submodule_permission', 'user_permission')
    op.drop_index('idx_user_permission_active', 'user_permission')
    op.drop_table('user_permission')
    op.drop_index('idx_submodule_module', 'permission_submodule')
    op.drop_table('permission_submodule')
    op.drop_index('idx_module_category', 'permission_module')
    op.drop_table('permission_module')
    op.drop_table('permission_category')