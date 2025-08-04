"""Implementa sistema unificado de permissões

Revision ID: 55f23dc84a3b
Revises: 2b5f3637c189
Create Date: 2025-07-28 19:35:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '55f23dc84a3b'
down_revision = '2b5f3637c189'
branch_labels = None
depends_on = None


def upgrade():
    # 1. CATEGORIAS DE PERMISSÃO
    op.create_table('permission_category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('nome_exibicao', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('icone', sa.String(length=50), nullable=True),
        sa.Column('cor', sa.String(length=7), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    
    # 2. MÓDULOS DE PERMISSÃO
    op.create_table('permission_module',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('nome_exibicao', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('icone', sa.String(length=50), nullable=True),
        sa.Column('cor', sa.String(length=7), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['permission_category.id'], ),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'nome', name='uq_module_category_name')
    )
    op.create_index('idx_module_category', 'permission_module', ['category_id', 'ativo'], unique=False)
    
    # 3. SUBMÓDULOS DE PERMISSÃO
    op.create_table('permission_submodule',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('nome_exibicao', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('route_pattern', sa.String(length=200), nullable=True),
        sa.Column('critical_level', sa.String(length=10), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['module_id'], ['permission_module.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('module_id', 'nome', name='uq_submodule_module_name'),
        sa.CheckConstraint("critical_level IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')", name='ck_critical_level')
    )
    op.create_index('idx_submodule_module', 'permission_submodule', ['module_id', 'ativo'], unique=False)
    
    # 4. PERFIS DE USUÁRIO
    op.create_table('perfil_usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.Column('nome_exibicao', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('nivel_hierarquico', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    
    # 5. VENDEDORES
    op.create_table('vendedor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('telefone', sa.String(length=20), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo')
    )
    
    # 6. EQUIPES DE VENDAS
    op.create_table('equipe_vendas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('gerente_id', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['gerente_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo')
    )
    
    # 7. TEMPLATES DE PERMISSÃO
    op.create_table('permission_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('categoria', sa.String(length=50), nullable=True),
        sa.Column('template_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo')
    )
    
    # 8. PERMISSÕES DE USUÁRIO
    op.create_table('user_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('can_delete', sa.Boolean(), nullable=False),
        sa.Column('can_export', sa.Boolean(), nullable=False),
        sa.Column('custom_override', sa.Boolean(), nullable=False),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_user_entity_permission'),
        sa.CheckConstraint("entity_type IN ('CATEGORY', 'MODULE', 'SUBMODULE')", name='ck_entity_type')
    )
    op.create_index('idx_entity_permission', 'user_permission', ['entity_type', 'entity_id', 'ativo'], unique=False)
    op.create_index('idx_user_permission_active', 'user_permission', ['user_id', 'ativo'], unique=False)
    
    # 9. VÍNCULOS USUÁRIO-VENDEDOR
    op.create_table('user_vendedor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vendedor_id', sa.Integer(), nullable=False),
        sa.Column('tipo_acesso', sa.String(length=20), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('adicionado_por', sa.Integer(), nullable=True),
        sa.Column('adicionado_em', sa.DateTime(), nullable=False),
        sa.Column('observacoes', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['adicionado_por'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['vendedor_id'], ['vendedor.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'vendedor_id', name='uq_user_vendedor')
    )
    op.create_index('idx_user_vendedor_active', 'user_vendedor', ['user_id', 'ativo'], unique=False)
    
    # 10. VÍNCULOS USUÁRIO-EQUIPE
    op.create_table('user_equipe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('equipe_id', sa.Integer(), nullable=False),
        sa.Column('cargo_equipe', sa.String(length=50), nullable=True),
        sa.Column('tipo_acesso', sa.String(length=20), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('adicionado_por', sa.Integer(), nullable=True),
        sa.Column('adicionado_em', sa.DateTime(), nullable=False),
        sa.Column('observacoes', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['adicionado_por'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['equipe_id'], ['equipe_vendas.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'equipe_id', name='uq_user_equipe')
    )
    op.create_index('idx_user_equipe_active', 'user_equipe', ['user_id', 'ativo'], unique=False)
    
    # 11. PERMISSÕES POR VENDEDOR
    op.create_table('vendedor_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendedor_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['vendedor_id'], ['vendedor.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vendedor_id', 'entity_type', 'entity_id', name='uq_vendedor_permission')
    )
    op.create_index('idx_vendedor_permission', 'vendedor_permission', ['vendedor_id', 'ativo'], unique=False)
    
    # 12. PERMISSÕES POR EQUIPE
    op.create_table('equipe_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipe_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False),
        sa.Column('can_edit', sa.Boolean(), nullable=False),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['equipe_id'], ['equipe_vendas.id'], ),
        sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('equipe_id', 'entity_type', 'entity_id', name='uq_equipe_permission')
    )
    op.create_index('idx_equipe_permission', 'equipe_permission', ['equipe_id', 'ativo'], unique=False)
    
    # 13. LOG DE PERMISSÕES
    op.create_table('permission_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_log_action_timestamp', 'permission_log', ['action', 'timestamp'], unique=False)
    op.create_index('idx_log_result', 'permission_log', ['result', 'timestamp'], unique=False)
    op.create_index('idx_log_user_timestamp', 'permission_log', ['user_id', 'timestamp'], unique=False)
    op.create_index(None, 'permission_log', ['timestamp'], unique=False)
    
    # 14. OPERAÇÕES EM LOTE
    op.create_table('batch_operation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('executed_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('affected_users', sa.Integer(), nullable=True),
        sa.Column('affected_permissions', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['executed_by'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 15. CACHE DE PERMISSÕES
    op.create_table('permission_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('permission_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key')
    )
    op.create_index('idx_cache_expires', 'permission_cache', ['expires_at'], unique=False)
    op.create_index('idx_cache_user', 'permission_cache', ['user_id'], unique=False)


def downgrade():
    # Drop all tables in reverse order
    op.drop_index('idx_cache_user', table_name='permission_cache')
    op.drop_index('idx_cache_expires', table_name='permission_cache')
    op.drop_table('permission_cache')
    op.drop_table('batch_operation')
    op.drop_index(None, table_name='permission_log')
    op.drop_index('idx_log_user_timestamp', table_name='permission_log')
    op.drop_index('idx_log_result', table_name='permission_log')
    op.drop_index('idx_log_action_timestamp', table_name='permission_log')
    op.drop_table('permission_log')
    op.drop_index('idx_equipe_permission', table_name='equipe_permission')
    op.drop_table('equipe_permission')
    op.drop_index('idx_vendedor_permission', table_name='vendedor_permission')
    op.drop_table('vendedor_permission')
    op.drop_index('idx_user_equipe_active', table_name='user_equipe')
    op.drop_table('user_equipe')
    op.drop_index('idx_user_vendedor_active', table_name='user_vendedor')
    op.drop_table('user_vendedor')
    op.drop_index('idx_user_permission_active', table_name='user_permission')
    op.drop_index('idx_entity_permission', table_name='user_permission')
    op.drop_table('user_permission')
    op.drop_table('permission_template')
    op.drop_table('equipe_vendas')
    op.drop_table('vendedor')
    op.drop_table('perfil_usuario')
    op.drop_index('idx_submodule_module', table_name='permission_submodule')
    op.drop_table('permission_submodule')
    op.drop_index('idx_module_category', table_name='permission_module')
    op.drop_table('permission_module')
    op.drop_table('permission_category')