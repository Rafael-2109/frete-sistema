"""Add hierarchical permission system

Revision ID: permission_system_v1
Revises: add_permissions_equipe_vendas
Create Date: 2025-07-26 17:35:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'permission_system_v1'
down_revision = 'add_permissions_equipe_vendas'
branch_labels = None
depends_on = None


def upgrade():
    # Check if permission_category table exists
    conn = op.get_bind()
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'permission_category')").scalar():
        # Create permission_category table
        op.create_table('permission_category',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(length=50), nullable=False),
            sa.Column('nome_exibicao', sa.String(length=100), nullable=False),
            sa.Column('descricao', sa.String(length=255), nullable=True),
            sa.Column('icone', sa.String(length=50), nullable=True, server_default='📁'),
            sa.Column('cor', sa.String(length=7), nullable=True, server_default='#6c757d'),
            sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nome')
        )
    
    # Check if sub_module table exists
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sub_module')").scalar():
        # Create sub_module table
        op.create_table('sub_module',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('modulo_id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(length=50), nullable=False),
            sa.Column('nome_exibicao', sa.String(length=100), nullable=False),
            sa.Column('descricao', sa.String(length=255), nullable=True),
            sa.Column('icone', sa.String(length=50), nullable=True),
            sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['modulo_id'], ['modulo_sistema.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('modulo_id', 'nome')
        )
        
        op.create_index('idx_submodule_ativo', 'sub_module', ['modulo_id', 'ativo'], unique=False)
    
    # Check if permission_template table exists
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'permission_template')").scalar():
        # Create permission_template table
        op.create_table('permission_template',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(length=100), nullable=False),
            sa.Column('descricao', sa.String(length=255), nullable=True),
            sa.Column('perfil_id', sa.Integer(), nullable=True),
            sa.Column('permissions_json', sa.Text(), nullable=False),
            sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('criado_por', sa.Integer(), nullable=True),
            sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('atualizado_em', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
            sa.ForeignKeyConstraint(['perfil_id'], ['perfil_usuario.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nome')
        )
    
    # Check if batch_permission_operation table exists
    if not conn.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'batch_permission_operation')").scalar():
        # Create batch_permission_operation table
        op.create_table('batch_permission_operation',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tipo_operacao', sa.String(length=50), nullable=False),
            sa.Column('descricao', sa.String(length=255), nullable=True),
            sa.Column('usuarios_afetados', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('permissoes_alteradas', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('detalhes_json', sa.Text(), nullable=True),
            sa.Column('executado_por', sa.Integer(), nullable=False),
            sa.Column('executado_em', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('status', sa.String(length=20), nullable=True, server_default='CONCLUIDO'),
            sa.Column('erro_detalhes', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['executado_por'], ['usuarios.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Add new columns to existing tables if they don't exist
    try:
        op.add_column('modulo_sistema', sa.Column('category_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_modulo_category', 'modulo_sistema', 'permission_category', ['category_id'], ['id'])
    except:
        pass
        
    try:
        op.add_column('modulo_sistema', sa.Column('parent_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_modulo_parent', 'modulo_sistema', 'modulo_sistema', ['parent_id'], ['id'])
    except:
        pass
        
    try:
        op.add_column('modulo_sistema', sa.Column('nivel_hierarquico', sa.Integer(), nullable=False, server_default='0'))
    except:
        pass
        
    # Add submodulo_id to funcao_modulo if it exists
    if op.get_bind().execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'funcao_modulo')").scalar():
        try:
            op.add_column('funcao_modulo', sa.Column('submodulo_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_funcao_submodulo', 'funcao_modulo', 'sub_module', ['submodulo_id'], ['id'])
        except:
            pass


def downgrade():
    # Drop foreign keys first
    if op.get_bind().execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'funcao_modulo')").scalar():
        try:
            op.drop_constraint('fk_funcao_submodulo', 'funcao_modulo', type_='foreignkey')
            op.drop_column('funcao_modulo', 'submodulo_id')
        except:
            pass
    
    try:
        op.drop_constraint('fk_modulo_parent', 'modulo_sistema', type_='foreignkey')
        op.drop_constraint('fk_modulo_category', 'modulo_sistema', type_='foreignkey')
        op.drop_column('modulo_sistema', 'nivel_hierarquico')
        op.drop_column('modulo_sistema', 'parent_id')
        op.drop_column('modulo_sistema', 'category_id')
    except:
        pass
    
    # Drop tables
    op.drop_table('batch_permission_operation')
    op.drop_table('permission_template')
    op.drop_index('idx_submodule_ativo', table_name='sub_module')
    op.drop_table('sub_module')
    op.drop_table('permission_category')