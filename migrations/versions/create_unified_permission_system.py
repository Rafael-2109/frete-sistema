"""create unified permission system

Revision ID: create_unified_permission_system
Revises: sistema_permissoes_funcional
Create Date: 2025-07-29 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_unified_permission_system'
down_revision = 'sistema_permissoes_funcional'
branch_labels = None
depends_on = None


def upgrade():
    """
    Cria todas as tabelas do sistema unificado de permissões.
    Se as tabelas já existirem, não faz nada.
    """
    
    # 1. Criar tabela de categorias se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS permission_category (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(50) UNIQUE NOT NULL,
            nome_exibicao VARCHAR(100) NOT NULL,
            descricao VARCHAR(255),
            icone VARCHAR(50) DEFAULT 'folder',
            cor VARCHAR(7) DEFAULT '#007bff',
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por INTEGER REFERENCES usuarios(id)
        );
    """)
    
    # 2. Criar tabela de módulos se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS permission_module (
            id SERIAL PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES permission_category(id),
            nome VARCHAR(50) NOT NULL,
            nome_exibicao VARCHAR(100) NOT NULL,
            descricao VARCHAR(255),
            icone VARCHAR(50) DEFAULT 'file',
            cor VARCHAR(7) DEFAULT '#6c757d',
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por INTEGER REFERENCES usuarios(id),
            CONSTRAINT uq_module_category_name UNIQUE (category_id, nome)
        );
    """)
    
    # Criar índice se não existir
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_module_category 
        ON permission_module(category_id, ativo);
    """)
    
    # 3. Criar tabela de submódulos se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS permission_submodule (
            id SERIAL PRIMARY KEY,
            module_id INTEGER NOT NULL REFERENCES permission_module(id),
            nome VARCHAR(50) NOT NULL,
            nome_exibicao VARCHAR(100) NOT NULL,
            descricao VARCHAR(255),
            route_pattern VARCHAR(200),
            critical_level VARCHAR(10) DEFAULT 'NORMAL' CHECK (critical_level IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')),
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por INTEGER REFERENCES usuarios(id),
            CONSTRAINT uq_submodule_module_name UNIQUE (module_id, nome)
        );
    """)
    
    # Criar índice se não existir
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_submodule_module 
        ON permission_submodule(module_id, ativo);
    """)
    
    # 4. Criar tabela de permissões de usuário se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_permission (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES usuarios(id),
            submodule_id INTEGER NOT NULL REFERENCES permission_submodule(id),
            can_view BOOLEAN DEFAULT FALSE NOT NULL,
            can_edit BOOLEAN DEFAULT FALSE NOT NULL,
            granted_by INTEGER REFERENCES usuarios(id),
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            CONSTRAINT uq_user_submodule_permission UNIQUE (user_id, submodule_id)
        );
    """)
    
    # Criar índices se não existirem
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_permission_active 
        ON user_permission(user_id, ativo);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_submodule_permission 
        ON user_permission(submodule_id, ativo);
    """)
    
    # 5. Criar tabela de vendedores se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS vendedor (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(50) UNIQUE NOT NULL,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(120),
            telefone VARCHAR(20),
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por INTEGER REFERENCES usuarios(id)
        );
    """)
    
    # 6. Criar tabela de equipes de vendas se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS equipe_vendas (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(50) UNIQUE NOT NULL,
            nome VARCHAR(100) NOT NULL,
            descricao VARCHAR(255),
            gerente_id INTEGER REFERENCES usuarios(id),
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por INTEGER REFERENCES usuarios(id)
        );
    """)
    
    # 7. Criar tabela de vínculo usuário-vendedor se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_vendedor (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES usuarios(id),
            vendedor_id INTEGER NOT NULL REFERENCES vendedor(id),
            tipo_acesso VARCHAR(20) DEFAULT 'view',
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            adicionado_por INTEGER REFERENCES usuarios(id),
            adicionado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            observacoes VARCHAR(255),
            CONSTRAINT uq_user_vendedor UNIQUE (user_id, vendedor_id)
        );
    """)
    
    # Criar índice se não existir
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_vendedor_active 
        ON user_vendedor(user_id, ativo);
    """)
    
    # 8. Criar tabela de vínculo usuário-equipe se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_equipe (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES usuarios(id),
            equipe_id INTEGER NOT NULL REFERENCES equipe_vendas(id),
            cargo_equipe VARCHAR(50),
            tipo_acesso VARCHAR(20) DEFAULT 'member',
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            adicionado_por INTEGER REFERENCES usuarios(id),
            adicionado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            observacoes VARCHAR(255),
            CONSTRAINT uq_user_equipe UNIQUE (user_id, equipe_id)
        );
    """)
    
    # Criar índice se não existir
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_equipe_active 
        ON user_equipe(user_id, ativo);
    """)
    
    # 9. Criar tabela de permissões de vendedor se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS vendedor_permission (
            id SERIAL PRIMARY KEY,
            vendedor_id INTEGER NOT NULL REFERENCES vendedor(id),
            submodule_id INTEGER NOT NULL REFERENCES permission_submodule(id),
            can_view BOOLEAN DEFAULT FALSE NOT NULL,
            can_edit BOOLEAN DEFAULT FALSE NOT NULL,
            granted_by INTEGER REFERENCES usuarios(id),
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            CONSTRAINT uq_vendedor_submodule UNIQUE (vendedor_id, submodule_id)
        );
    """)
    
    # Criar índice se não existir
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vendedor_permission 
        ON vendedor_permission(vendedor_id, ativo);
    """)
    
    # 10. Criar tabela de permissões de equipe se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS equipe_permission (
            id SERIAL PRIMARY KEY,
            equipe_id INTEGER NOT NULL REFERENCES equipe_vendas(id),
            submodule_id INTEGER NOT NULL REFERENCES permission_submodule(id),
            can_view BOOLEAN DEFAULT FALSE NOT NULL,
            can_edit BOOLEAN DEFAULT FALSE NOT NULL,
            granted_by INTEGER REFERENCES usuarios(id),
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            CONSTRAINT uq_equipe_submodule UNIQUE (equipe_id, submodule_id)
        );
    """)
    
    # Criar índice se não existir
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_equipe_permission 
        ON equipe_permission(equipe_id, ativo);
    """)
    
    # 11. Criar tabela de templates de permissão se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS permission_template (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            codigo VARCHAR(50) UNIQUE NOT NULL,
            descricao VARCHAR(255),
            categoria VARCHAR(50) DEFAULT 'custom',
            template_data JSON NOT NULL,
            is_system BOOLEAN DEFAULT FALSE NOT NULL,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por INTEGER REFERENCES usuarios(id),
            atualizado_em TIMESTAMP
        );
    """)
    
    # 12. Criar tabela de perfis de usuário se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS perfil_usuario (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(50) UNIQUE NOT NULL,
            nome_exibicao VARCHAR(100) NOT NULL,
            descricao VARCHAR(255),
            nivel_hierarquico INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por INTEGER REFERENCES usuarios(id)
        );
    """)
    
    # 13. Criar tabela de logs de permissão se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS permission_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES usuarios(id),
            action VARCHAR(50) NOT NULL,
            entity_type VARCHAR(20),
            entity_id INTEGER,
            details JSON,
            result VARCHAR(20) DEFAULT 'SUCCESS',
            ip_address VARCHAR(45),
            user_agent VARCHAR(255),
            session_id VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
    """)
    
    # Criar índices se não existirem
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_log_user_timestamp 
        ON permission_log(user_id, timestamp);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_log_action_timestamp 
        ON permission_log(action, timestamp);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_log_result 
        ON permission_log(result, timestamp);
    """)
    
    # 14. Criar tabela de operações em lote se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS batch_operation (
            id SERIAL PRIMARY KEY,
            operation_type VARCHAR(20) NOT NULL,
            description VARCHAR(255),
            executed_by INTEGER NOT NULL REFERENCES usuarios(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            status VARCHAR(20) DEFAULT 'PENDING',
            affected_users INTEGER DEFAULT 0,
            affected_permissions INTEGER DEFAULT 0,
            details JSON,
            error_details TEXT
        );
    """)
    
    # 15. Criar tabela de cache de permissões se não existir
    op.execute("""
        CREATE TABLE IF NOT EXISTS permission_cache (
            id SERIAL PRIMARY KEY,
            cache_key VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER REFERENCES usuarios(id),
            permission_data JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL
        );
    """)
    
    # Criar índices se não existirem
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cache_user 
        ON permission_cache(user_id);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cache_expires 
        ON permission_cache(expires_at);
    """)


def downgrade():
    """
    Remove todas as tabelas do sistema de permissões em ordem reversa
    """
    # Remover tabelas em ordem reversa para respeitar foreign keys
    tables = [
        'permission_cache',
        'batch_operation',
        'permission_log',
        'perfil_usuario',
        'permission_template',
        'equipe_permission',
        'vendedor_permission',
        'user_equipe',
        'user_vendedor',
        'equipe_vendas',
        'vendedor',
        'user_permission',
        'permission_submodule',
        'permission_module',
        'permission_category'
    ]
    
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")