"""Unify permission system
Revision ID: unify_permission_system
Revises: portfolio_mcp_integration
Create Date: 2025-01-28 10:00:00.000000

Sistema unificado de permissões com:
- 3 categorias principais (Operacional, Financeiro, Administrativo)
- 5 módulos distribuídos entre as categorias
- 10 submódulos com funções específicas
- Migração dos dados do sistema antigo
- Sistema de rollback completo
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'unify_permission_system'
down_revision = 'portfolio_mcp_integration'
branch_labels = None
depends_on = None


def upgrade():
    """
    Implementa o novo sistema de permissões unificado
    """
    connection = op.get_bind()
    
    # 1. Verificar se as tabelas novas já existem (evitar duplicação)
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # 2. Criar tabelas do novo sistema hierárquico se não existirem
    if 'permission_category' not in existing_tables:
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
        
    if 'permission_module' not in existing_tables:
        op.create_table('permission_module',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('category_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('display_name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('icon', sa.String(length=50), nullable=True),
            sa.Column('color', sa.String(length=7), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['category_id'], ['permission_category.id'], ),
            sa.ForeignKeyConstraint(['created_by'], ['usuarios.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_module_category', 'permission_module', ['category_id', 'active'], unique=False)
        op.create_unique_constraint('uq_module_category_name', 'permission_module', ['category_id', 'name'])
        
    if 'permission_submodule' not in existing_tables:
        op.create_table('permission_submodule',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('module_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('display_name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('route_pattern', sa.String(length=200), nullable=True),
            sa.Column('critical_level', sa.String(length=10), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['usuarios.id'], ),
            sa.ForeignKeyConstraint(['module_id'], ['permission_module.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_submodule_module', 'permission_submodule', ['module_id', 'active'], unique=False)
        op.create_unique_constraint('uq_submodule_module_name', 'permission_submodule', ['module_id', 'name'])
        
    if 'user_permission' not in existing_tables:
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
            sa.ForeignKeyConstraint(['granted_by'], ['usuarios.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_entity_permission', 'user_permission', ['entity_type', 'entity_id', 'active'], unique=False)
        op.create_index('idx_user_permission_active', 'user_permission', ['user_id', 'active'], unique=False)
        op.create_unique_constraint('uq_user_entity_permission', 'user_permission', ['user_id', 'entity_type', 'entity_id'])
        
    if 'permission_template' not in existing_tables:
        op.create_table('permission_template',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=True),
            sa.Column('template_data', sa.Text(), nullable=False),
            sa.Column('is_system', sa.Boolean(), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['usuarios.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code')
        )
        
    if 'batch_permission_operation' not in existing_tables:
        op.create_table('batch_permission_operation',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('operation_type', sa.String(length=20), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('executed_by', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('affected_users', sa.Integer(), nullable=True),
            sa.Column('affected_permissions', sa.Integer(), nullable=True),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('error_details', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['executed_by'], ['usuarios.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
    if 'permission_cache' not in existing_tables:
        op.create_table('permission_cache',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('cache_key', sa.String(length=255), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('permission_data', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['usuarios.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('cache_key')
        )
        op.create_index('idx_cache_expires', 'permission_cache', ['expires_at'], unique=False)
        op.create_index('idx_cache_user', 'permission_cache', ['user_id'], unique=False)
    
    # 3. Inserir dados iniciais (categorias, módulos e submódulos)
    # Inserir categorias
    connection.execute(sa.text("""
        INSERT INTO permission_category (nome, nome_exibicao, descricao, icone, cor, ordem, ativo, criado_em)
        VALUES 
        ('operacional', 'Operacional', 'Módulos de operação e logística', '🚚', '#28a745', 1, true, NOW()),
        ('financeiro', 'Financeiro', 'Módulos financeiros e faturamento', '💰', '#ffc107', 2, true, NOW()),
        ('administrativo', 'Administrativo', 'Módulos administrativos e gestão', '⚙️', '#dc3545', 3, true, NOW())
        ON CONFLICT (nome) DO NOTHING;
    """))
    
    # 4. Migrar dados do sistema antigo
    # Mapear módulos antigos para novas categorias
    module_mapping = {
        'carteira': ('operacional', 'carteira_pedidos', 'Carteira de Pedidos', '📋'),
        'embarques': ('operacional', 'embarques_logistica', 'Embarques e Logística', '🚛'),
        'portaria': ('operacional', 'controle_portaria', 'Controle de Portaria', '🚪'),
        'faturamento': ('financeiro', 'faturamento_nf', 'Faturamento e NF', '💰'),
        'financeiro': ('financeiro', 'gestao_financeira', 'Gestão Financeira', '💳'),
    }
    
    # Migrar módulos existentes para o novo sistema
    for old_name, (category, new_name, display_name, icon) in module_mapping.items():
        # Buscar ID da categoria
        cat_result = connection.execute(
            sa.text("SELECT id FROM permission_category WHERE nome = :cat"),
            {"cat": category}
        ).fetchone()
        
        if cat_result:
            cat_id = cat_result[0]
            
            # Inserir módulo na nova estrutura
            connection.execute(sa.text("""
                INSERT INTO permission_module (category_id, name, display_name, icon, active, created_at)
                VALUES (:cat_id, :name, :display_name, :icon, true, NOW())
                ON CONFLICT (category_id, name) DO NOTHING;
            """), {
                "cat_id": cat_id,
                "name": new_name,
                "display_name": display_name,
                "icon": icon
            })
            
            # Buscar ID do novo módulo
            mod_result = connection.execute(
                sa.text("SELECT id FROM permission_module WHERE name = :name"),
                {"name": new_name}
            ).fetchone()
            
            if mod_result:
                new_mod_id = mod_result[0]
                
                # Migrar funções para submódulos
                old_functions = connection.execute(sa.text("""
                    SELECT fm.nome, fm.nome_exibicao, fm.rota_padrao, fm.nivel_critico
                    FROM funcao_modulo fm
                    JOIN modulo_sistema ms ON fm.modulo_id = ms.id
                    WHERE ms.nome = :old_name AND fm.ativo = true
                """), {"old_name": old_name})
                
                for func in old_functions:
                    connection.execute(sa.text("""
                        INSERT INTO permission_submodule 
                        (module_id, name, display_name, route_pattern, critical_level, active, created_at)
                        VALUES (:mod_id, :name, :display_name, :route, :critical, true, NOW())
                        ON CONFLICT (module_id, name) DO NOTHING;
                    """), {
                        "mod_id": new_mod_id,
                        "name": func[0],
                        "display_name": func[1],
                        "route": func[2],
                        "critical": func[3] or 'NORMAL'
                    })
    
    # 5. Migrar permissões de usuários
    # Buscar todas as permissões ativas do sistema antigo
    old_permissions = connection.execute(sa.text("""
        SELECT DISTINCT 
            pu.usuario_id,
            ms.nome as modulo,
            fm.nome as funcao,
            pu.pode_visualizar,
            pu.pode_editar,
            pu.concedida_por,
            pu.concedida_em,
            pu.expira_em,
            pu.observacoes
        FROM permissao_usuario pu
        JOIN funcao_modulo fm ON pu.funcao_id = fm.id
        JOIN modulo_sistema ms ON fm.modulo_id = ms.id
        WHERE pu.ativo = true
    """))
    
    for perm in old_permissions:
        # Mapear para o novo sistema
        if perm[1] in module_mapping:
            _, new_module_name, _, _ = module_mapping[perm[1]]
            
            # Buscar ID do submódulo no novo sistema
            submod_result = connection.execute(sa.text("""
                SELECT ps.id 
                FROM permission_submodule ps
                JOIN permission_module pm ON ps.module_id = pm.id
                WHERE pm.name = :module AND ps.name = :function
            """), {"module": new_module_name, "function": perm[2]}).fetchone()
            
            if submod_result:
                # Inserir permissão no novo sistema
                connection.execute(sa.text("""
                    INSERT INTO user_permission 
                    (user_id, entity_type, entity_id, can_view, can_edit, can_delete, can_export,
                     custom_override, granted_by, granted_at, expires_at, reason, active)
                    VALUES (:user_id, 'SUBMODULE', :entity_id, :can_view, :can_edit, false, false,
                            false, :granted_by, :granted_at, :expires_at, :reason, true)
                    ON CONFLICT (user_id, entity_type, entity_id) DO UPDATE
                    SET can_view = EXCLUDED.can_view,
                        can_edit = EXCLUDED.can_edit,
                        expires_at = EXCLUDED.expires_at;
                """), {
                    "user_id": perm[0],
                    "entity_id": submod_result[0],
                    "can_view": perm[3],
                    "can_edit": perm[4],
                    "granted_by": perm[5],
                    "granted_at": perm[6],
                    "expires_at": perm[7],
                    "reason": perm[8]
                })
    
    # 6. Criar templates de permissão para cada perfil
    templates = [
        {
            'name': 'Template Vendedor',
            'code': 'template_vendedor',
            'category': 'roles',
            'permissions': {
                'carteira_pedidos': {
                    'listar': {'view': True, 'edit': False},
                    'visualizar': {'view': True, 'edit': False}
                },
                'embarques_logistica': {
                    'listar': {'view': True, 'edit': False},
                    'visualizar': {'view': True, 'edit': False}
                }
            }
        },
        {
            'name': 'Template Gerente Comercial',
            'code': 'template_gerente_comercial',
            'category': 'roles',
            'permissions': {
                'carteira_pedidos': {
                    'listar': {'view': True, 'edit': True},
                    'visualizar': {'view': True, 'edit': True},
                    'gerar_separacao': {'view': True, 'edit': True},
                    'baixar_faturamento': {'view': True, 'edit': True}
                },
                'faturamento_nf': {
                    'listar': {'view': True, 'edit': True},
                    'visualizar': {'view': True, 'edit': True},
                    'editar': {'view': True, 'edit': True},
                    'exportar': {'view': True, 'edit': True}
                }
            }
        },
        {
            'name': 'Template Financeiro',
            'code': 'template_financeiro',
            'category': 'roles',
            'permissions': {
                'faturamento_nf': {
                    'listar': {'view': True, 'edit': True},
                    'visualizar': {'view': True, 'edit': True},
                    'editar': {'view': True, 'edit': True},
                    'importar': {'view': True, 'edit': True},
                    'exportar': {'view': True, 'edit': True}
                },
                'gestao_financeira': {
                    'lancamento_freteiros': {'view': True, 'edit': True},
                    'aprovar_faturas': {'view': True, 'edit': True},
                    'relatorios': {'view': True, 'edit': True}
                }
            }
        },
        {
            'name': 'Template Logística',
            'code': 'template_logistica',
            'category': 'roles',
            'permissions': {
                'embarques_logistica': {
                    'listar': {'view': True, 'edit': True},
                    'criar': {'view': True, 'edit': True},
                    'editar': {'view': True, 'edit': True},
                    'finalizar': {'view': True, 'edit': True}
                },
                'controle_portaria': {
                    'dashboard': {'view': True, 'edit': True},
                    'registrar_movimento': {'view': True, 'edit': True},
                    'historico': {'view': True, 'edit': False}
                }
            }
        },
        {
            'name': 'Template Portaria',
            'code': 'template_portaria',
            'category': 'roles',
            'permissions': {
                'controle_portaria': {
                    'dashboard': {'view': True, 'edit': False},
                    'registrar_movimento': {'view': True, 'edit': True},
                    'historico': {'view': True, 'edit': False}
                },
                'embarques_logistica': {
                    'listar': {'view': True, 'edit': False},
                    'visualizar': {'view': True, 'edit': False}
                }
            }
        }
    ]
    
    for template in templates:
        connection.execute(sa.text("""
            INSERT INTO permission_template 
            (name, code, description, category, template_data, is_system, active, created_at)
            VALUES (:name, :code, :desc, :category, :data, true, true, NOW())
            ON CONFLICT (code) DO NOTHING;
        """), {
            "name": template['name'],
            "code": template['code'],
            "desc": f"Template padrão para perfil {template['name']}",
            "category": template['category'],
            "data": json.dumps(template['permissions'])
        })
    
    # 7. Registrar operação de migração
    connection.execute(sa.text("""
        INSERT INTO batch_permission_operation 
        (operation_type, description, executed_by, created_at, completed_at, status, details)
        VALUES ('MIGRATION', 'Migração do sistema de permissões antigo para o novo sistema unificado',
                1, NOW(), NOW(), 'COMPLETED', :details);
    """), {
        "details": json.dumps({
            "migration_version": "unify_permission_system",
            "categories_created": 3,
            "modules_migrated": len(module_mapping),
            "templates_created": len(templates)
        })
    })


def downgrade():
    """
    Reverte para o sistema antigo de permissões
    """
    connection = op.get_bind()
    
    # 1. Registrar operação de rollback
    connection.execute(sa.text("""
        INSERT INTO batch_permission_operation 
        (operation_type, description, executed_by, created_at, status)
        VALUES ('ROLLBACK', 'Rollback do sistema unificado de permissões', 1, NOW(), 'IN_PROGRESS');
    """))
    
    # 2. Backup das permissões atuais antes de reverter
    # Criar tabela temporária para backup
    op.create_table('_backup_user_permissions',
        sa.Column('id', sa.Integer()),
        sa.Column('user_id', sa.Integer()),
        sa.Column('entity_type', sa.String()),
        sa.Column('entity_id', sa.Integer()),
        sa.Column('can_view', sa.Boolean()),
        sa.Column('can_edit', sa.Boolean()),
        sa.Column('can_delete', sa.Boolean()),
        sa.Column('can_export', sa.Boolean()),
        sa.Column('granted_by', sa.Integer()),
        sa.Column('granted_at', sa.DateTime()),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('reason', sa.String()),
        sa.Column('active', sa.Boolean())
    )
    
    # Copiar dados para backup
    connection.execute(sa.text("""
        INSERT INTO _backup_user_permissions
        SELECT id, user_id, entity_type, entity_id, can_view, can_edit, can_delete, 
               can_export, granted_by, granted_at, expires_at, reason, active
        FROM user_permission;
    """))
    
    # 3. Restaurar permissões para o sistema antigo
    # Buscar permissões de submódulos e converter de volta
    permissions_to_restore = connection.execute(sa.text("""
        SELECT 
            up.user_id,
            pm.name as module_name,
            ps.name as function_name,
            up.can_view,
            up.can_edit,
            up.granted_by,
            up.granted_at,
            up.expires_at,
            up.reason
        FROM user_permission up
        JOIN permission_submodule ps ON up.entity_id = ps.id
        JOIN permission_module pm ON ps.module_id = pm.id
        WHERE up.entity_type = 'SUBMODULE' AND up.active = true
    """))
    
    # Mapear de volta para o sistema antigo
    reverse_mapping = {
        'carteira_pedidos': 'carteira',
        'embarques_logistica': 'embarques',
        'controle_portaria': 'portaria',
        'faturamento_nf': 'faturamento',
        'gestao_financeira': 'financeiro'
    }
    
    for perm in permissions_to_restore:
        if perm[1] in reverse_mapping:
            old_module = reverse_mapping[perm[1]]
            
            # Buscar IDs no sistema antigo
            result = connection.execute(sa.text("""
                SELECT fm.id
                FROM funcao_modulo fm
                JOIN modulo_sistema ms ON fm.modulo_id = ms.id
                WHERE ms.nome = :module AND fm.nome = :function
            """), {"module": old_module, "function": perm[2]}).fetchone()
            
            if result:
                # Restaurar permissão no sistema antigo
                connection.execute(sa.text("""
                    INSERT INTO permissao_usuario 
                    (usuario_id, funcao_id, pode_visualizar, pode_editar, 
                     concedida_por, concedida_em, expira_em, observacoes, ativo)
                    VALUES (:user_id, :func_id, :can_view, :can_edit,
                            :granted_by, :granted_at, :expires_at, :reason, true)
                    ON CONFLICT (usuario_id, funcao_id) DO UPDATE
                    SET pode_visualizar = EXCLUDED.pode_visualizar,
                        pode_editar = EXCLUDED.pode_editar,
                        ativo = true;
                """), {
                    "user_id": perm[0],
                    "func_id": result[0],
                    "can_view": perm[3],
                    "can_edit": perm[4],
                    "granted_by": perm[5],
                    "granted_at": perm[6],
                    "expires_at": perm[7],
                    "reason": perm[8]
                })
    
    # 4. Remover tabelas do novo sistema (em ordem reversa de dependências)
    op.drop_table('permission_cache')
    op.drop_table('batch_permission_operation')
    op.drop_table('permission_template')
    op.drop_table('user_permission')
    op.drop_table('permission_submodule')
    op.drop_table('permission_module')
    op.drop_table('permission_category')
    
    # 5. Limpar tabela de backup
    op.drop_table('_backup_user_permissions')