#!/usr/bin/env python3
"""
Script para aplicar a migration segura diretamente
"""

import os
from sqlalchemy import create_engine, text

def apply_safe_migration():
    """Aplica a migration segura diretamente"""
    database_url = os.environ.get('DATABASE_URL', 'postgresql://frete_user:frete_senha_2024@localhost:5432/frete_sistema')
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Inicia transação
        trans = conn.begin()
        
        try:
            print("🚀 Aplicando migration segura...")
            
            # 1. Criar tabela permission_cache
            print("   📝 Criando permission_cache...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS permission_cache (
                    id SERIAL PRIMARY KEY,
                    cache_key VARCHAR(255) NOT NULL UNIQUE,
                    user_id INTEGER REFERENCES usuarios(id),
                    permission_data JSON NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_expires ON permission_cache(expires_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cache_user ON permission_cache(user_id)"))
            
            # 2. Criar tabela submodule
            print("   📝 Criando submodule...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS submodule (
                    id SERIAL PRIMARY KEY,
                    modulo_id INTEGER NOT NULL REFERENCES modulo_sistema(id),
                    nome VARCHAR(50) NOT NULL,
                    nome_exibicao VARCHAR(100) NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT true
                )
            """))
            
            # 3. Criar tabela user_permission
            print("   📝 Criando user_permission...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_permission (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES usuarios(id),
                    entity_type VARCHAR(20) NOT NULL,
                    entity_id INTEGER NOT NULL,
                    can_view BOOLEAN NOT NULL DEFAULT false,
                    can_edit BOOLEAN NOT NULL DEFAULT false,
                    can_delete BOOLEAN NOT NULL DEFAULT false,
                    can_export BOOLEAN NOT NULL DEFAULT false,
                    custom_override BOOLEAN NOT NULL DEFAULT false,
                    granted_by INTEGER REFERENCES usuarios(id),
                    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    reason VARCHAR(255),
                    active BOOLEAN NOT NULL DEFAULT true,
                    CONSTRAINT uq_user_entity_permission UNIQUE (user_id, entity_type, entity_id)
                )
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_entity_permission ON user_permission(entity_type, entity_id, active)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_permission_active ON user_permission(user_id, active)"))
            
            # 4. Criar tabela permissao_equipe se não existir
            print("   📝 Criando permissao_equipe...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS permissao_equipe (
                    id SERIAL PRIMARY KEY,
                    equipe_id INTEGER NOT NULL REFERENCES equipe_vendas(id),
                    funcao_id INTEGER NOT NULL REFERENCES funcao_modulo(id),
                    pode_visualizar BOOLEAN NOT NULL DEFAULT false,
                    pode_editar BOOLEAN NOT NULL DEFAULT false,
                    concedida_por INTEGER REFERENCES usuarios(id),
                    concedida_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ativo BOOLEAN NOT NULL DEFAULT true,
                    CONSTRAINT uq_permissao_equipe_funcao UNIQUE (equipe_id, funcao_id)
                )
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_permissao_equipe_ativo ON permissao_equipe(equipe_id, ativo)"))
            
            # 5. Criar tabela permissao_vendedor se não existir
            print("   📝 Criando permissao_vendedor...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS permissao_vendedor (
                    id SERIAL PRIMARY KEY,
                    vendedor_id INTEGER NOT NULL REFERENCES vendedor(id),
                    funcao_id INTEGER NOT NULL REFERENCES funcao_modulo(id),
                    pode_visualizar BOOLEAN NOT NULL DEFAULT false,
                    pode_editar BOOLEAN NOT NULL DEFAULT false,
                    concedida_por INTEGER REFERENCES usuarios(id),
                    concedida_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ativo BOOLEAN NOT NULL DEFAULT true,
                    CONSTRAINT uq_permissao_vendedor_funcao UNIQUE (vendedor_id, funcao_id)
                )
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_permissao_vendedor_ativo ON permissao_vendedor(vendedor_id, ativo)"))
            
            # 6. Criar tabelas auxiliares de permissão
            print("   📝 Criando permission_module...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS permission_module (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    display_name VARCHAR(100) NOT NULL,
                    description VARCHAR(255),
                    icon VARCHAR(50),
                    active BOOLEAN NOT NULL DEFAULT true,
                    order_index INTEGER NOT NULL DEFAULT 0
                )
            """))
            
            print("   📝 Criando permission_submodule...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS permission_submodule (
                    id SERIAL PRIMARY KEY,
                    module_id INTEGER NOT NULL REFERENCES permission_module(id),
                    name VARCHAR(100) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    description VARCHAR(255),
                    icon VARCHAR(50),
                    active BOOLEAN NOT NULL DEFAULT true,
                    order_index INTEGER NOT NULL DEFAULT 0,
                    CONSTRAINT uq_permission_submodule UNIQUE (module_id, name)
                )
            """))
            
            # 7. Atualizar versão da migration
            print("   📝 Atualizando versão da migration...")
            conn.execute(text("UPDATE alembic_version SET version_num = 'safe_permission_update'"))
            
            # Confirma transação
            trans.commit()
            print("✅ Migration segura aplicada com sucesso!")
            
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Erro ao aplicar migration: {e}")
            return False

if __name__ == "__main__":
    success = apply_safe_migration()
    if success:
        print("\n🎉 Todas as tabelas criadas com sucesso!")
    else:
        print("\n❌ Falha ao criar tabelas!")