"""Safe permission system update - Add only new tables

Revision ID: safe_permission_update
Revises: permission_system_v1
Create Date: 2025-07-27 10:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'safe_permission_update'
down_revision = 'permission_system_v1'
branch_labels = None
depends_on = None


def upgrade():
    """
    Migration segura que adiciona apenas as novas tabelas de permissão
    sem remover tabelas existentes que podem conter dados importantes.
    """
    conn = op.get_bind()
    
    # 1. Criar tabela permission_cache
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'permission_cache')").scalar():
        op.create_table('permission_cache',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('cache_key', sa.String(length=255), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('permission_data', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['usuarios.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('cache_key')
        )
        
        # Criar índices para permission_cache
        op.create_index('idx_cache_expires', 'permission_cache', ['expires_at'], unique=False)
        op.create_index('idx_cache_user', 'permission_cache', ['user_id'], unique=False)
    
    # 2. Criar tabela submodule (nova versão sem conflito com sub_module)
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'submodule')").scalar():
        op.create_table('submodule',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('modulo_id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(length=50), nullable=False),
            sa.Column('nome_exibicao', sa.String(length=100), nullable=False),
            sa.Column('ativo', sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(['modulo_id'], ['modulo_sistema.id']),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 3. Criar tabela user_permission
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_permission')").scalar():
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
            sa.Column('active', sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id']),
            sa.ForeignKeyConstraint(['user_id'], ['usuarios.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_user_entity_permission')
        )
        
        # Criar índices para user_permission
        op.create_index('idx_entity_permission', 'user_permission', ['entity_type', 'entity_id', 'active'], unique=False)
        op.create_index('idx_user_permission_active', 'user_permission', ['user_id', 'active'], unique=False)
    
    # 4. Verificar se permissao_equipe já existe antes de criar
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'permissao_equipe')").scalar():
        op.create_table('permissao_equipe',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('equipe_id', sa.Integer(), nullable=False),
            sa.Column('funcao_id', sa.Integer(), nullable=False),
            sa.Column('pode_visualizar', sa.Boolean(), nullable=False),
            sa.Column('pode_editar', sa.Boolean(), nullable=False),
            sa.Column('concedida_por', sa.Integer(), nullable=True),
            sa.Column('concedida_em', sa.DateTime(), nullable=False),
            sa.Column('ativo', sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(['concedida_por'], ['usuarios.id']),
            sa.ForeignKeyConstraint(['equipe_id'], ['equipe_vendas.id']),
            sa.ForeignKeyConstraint(['funcao_id'], ['funcao_modulo.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('equipe_id', 'funcao_id', name='uq_permissao_equipe_funcao')
        )
        
        # Criar índice para permissao_equipe
        op.create_index('idx_permissao_equipe_ativo', 'permissao_equipe', ['equipe_id', 'ativo'], unique=False)
    
    # 5. Verificar se permissao_vendedor já existe antes de criar
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'permissao_vendedor')").scalar():
        op.create_table('permissao_vendedor',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('vendedor_id', sa.Integer(), nullable=False),
            sa.Column('funcao_id', sa.Integer(), nullable=False),
            sa.Column('pode_visualizar', sa.Boolean(), nullable=False),
            sa.Column('pode_editar', sa.Boolean(), nullable=False),
            sa.Column('concedida_por', sa.Integer(), nullable=True),
            sa.Column('concedida_em', sa.DateTime(), nullable=False),
            sa.Column('ativo', sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(['concedida_por'], ['usuarios.id']),
            sa.ForeignKeyConstraint(['funcao_id'], ['funcao_modulo.id']),
            sa.ForeignKeyConstraint(['vendedor_id'], ['vendedor.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('vendedor_id', 'funcao_id', name='uq_permissao_vendedor_funcao')
        )
        
        # Criar índice para permissao_vendedor
        op.create_index('idx_permissao_vendedor_ativo', 'permissao_vendedor', ['vendedor_id', 'ativo'], unique=False)
    
    # 6. Criar tabelas auxiliares de permissão se não existirem
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'permission_module')").scalar():
        op.create_table('permission_module',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('display_name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('icon', sa.String(length=50), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
    
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'permission_submodule')").scalar():
        op.create_table('permission_submodule',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('module_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('display_name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('icon', sa.String(length=50), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['module_id'], ['permission_module.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('module_id', 'name')
        )
    
    print("✅ Migration segura aplicada com sucesso!")
    print("📊 Tabelas adicionadas:")
    print("   - permission_cache (cache de permissões)")
    print("   - submodule (submódulos do sistema)")
    print("   - user_permission (permissões de usuário)")
    print("   - permissao_equipe (permissões por equipe)")
    print("   - permissao_vendedor (permissões por vendedor)")
    print("   - permission_module (módulos de permissão)")
    print("   - permission_submodule (submódulos de permissão)")
    print("🛡️ Nenhuma tabela existente foi removida!")


def downgrade():
    """
    Remove apenas as tabelas criadas por esta migration,
    sem afetar tabelas existentes do sistema.
    """
    # Remove em ordem reversa das dependências
    op.drop_table('permission_submodule')
    op.drop_table('permission_module')
    
    # Remove índices antes das tabelas
    op.drop_index('idx_permissao_vendedor_ativo', table_name='permissao_vendedor')
    op.drop_table('permissao_vendedor')
    
    op.drop_index('idx_permissao_equipe_ativo', table_name='permissao_equipe')
    op.drop_table('permissao_equipe')
    
    op.drop_index('idx_user_permission_active', table_name='user_permission')
    op.drop_index('idx_entity_permission', table_name='user_permission')
    op.drop_table('user_permission')
    
    op.drop_table('submodule')
    
    op.drop_index('idx_cache_user', table_name='permission_cache')
    op.drop_index('idx_cache_expires', table_name='permission_cache')
    op.drop_table('permission_cache')