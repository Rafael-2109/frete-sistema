#!/usr/bin/env python
"""
Initialize permissions system for Render deployment
This script combines all necessary initialization steps
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['SKIP_CLAUDE_AI'] = 'true'

from app import create_app, db
from sqlalchemy import text
from app.permissions.module_scanner import ModuleScanner

def initialize_permissions():
    """Initialize complete permissions system"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Initializing permissions system...")
        
        # Step 1: Ensure admin user exists
        print("\n👤 Setting up admin user...")
        try:
            result = db.session.execute(text("""
                UPDATE usuarios 
                SET perfil = 'administrador',
                    perfil_nome = 'Administrador',
                    status = 'ativo'
                WHERE email = 'rafael6250@gmail.com'
                RETURNING id, email, perfil, perfil_nome
            """))
            
            user = result.fetchone()
            if user:
                print(f"✅ Admin user configured: {user[1]}")
            else:
                print("⚠️ Admin user not found - please create user first")
            
            db.session.commit()
        except Exception as e:
            print(f"⚠️ Error setting admin: {e}")
            db.session.rollback()
        
        # Step 2: Create vendor tables
        print("\n📊 Creating vendor and team tables...")
        tables = [
            ("vendedor", """CREATE TABLE IF NOT EXISTS vendedor (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(20) UNIQUE NOT NULL,
                nome VARCHAR(100) NOT NULL,
                razao_social VARCHAR(150),
                cnpj_cpf VARCHAR(20),
                email VARCHAR(100),
                telefone VARCHAR(20),
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por INTEGER REFERENCES usuarios(id)
            )"""),
            
            ("equipe_vendas", """CREATE TABLE IF NOT EXISTS equipe_vendas (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(20) UNIQUE NOT NULL,
                nome VARCHAR(100) NOT NULL,
                descricao TEXT,
                gerente VARCHAR(100),
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por INTEGER REFERENCES usuarios(id)
            )"""),
            
            ("usuario_vendedor", """CREATE TABLE IF NOT EXISTS usuario_vendedor (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                vendedor_id INTEGER NOT NULL REFERENCES vendedor(id),
                tipo_acesso VARCHAR(20) DEFAULT 'visualizar',
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(usuario_id, vendedor_id)
            )"""),
            
            ("usuario_equipe_vendas", """CREATE TABLE IF NOT EXISTS usuario_equipe_vendas (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                equipe_id INTEGER NOT NULL REFERENCES equipe_vendas(id),
                cargo_equipe VARCHAR(50) DEFAULT 'Membro',
                tipo_acesso VARCHAR(20) DEFAULT 'membro',
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(usuario_id, equipe_id)
            )""")
        ]
        
        for table_name, sql in tables:
            try:
                db.session.execute(text(sql))
                print(f"✅ Table '{table_name}' created/verified")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"✅ Table '{table_name}' already exists")
                else:
                    print(f"❌ Error with table '{table_name}': {e}")
        
        db.session.commit()
        
        # Step 3: Initialize module scanner
        print("\n🔍 Scanning application modules...")
        try:
            success = ModuleScanner.initialize_permissions_from_scan()
            if success:
                print("✅ Permission structure initialized from scan")
            else:
                print("⚠️ Could not initialize from scan - may already exist")
        except Exception as e:
            print(f"⚠️ Error scanning modules: {e}")
        
        # Step 4: Insert sample vendor/team data
        print("\n📝 Creating sample data...")
        try:
            db.session.execute(text("""
                INSERT INTO vendedor (codigo, nome, razao_social, cnpj_cpf, email, telefone)
                VALUES 
                    ('V001', 'Vendedor Exemplo 1', 'Exemplo Ltda', '12.345.678/0001-90', 'vendedor1@example.com', '(11) 1234-5678'),
                    ('V002', 'Vendedor Exemplo 2', 'Teste SA', '98.765.432/0001-10', 'vendedor2@example.com', '(11) 9876-5432')
                ON CONFLICT (codigo) DO NOTHING
            """))
            
            db.session.execute(text("""
                INSERT INTO equipe_vendas (codigo, nome, descricao, gerente)
                VALUES 
                    ('EQ001', 'Equipe Sul', 'Equipe de vendas região Sul', 'João Silva'),
                    ('EQ002', 'Equipe Norte', 'Equipe de vendas região Norte', 'Maria Santos')
                ON CONFLICT (codigo) DO NOTHING
            """))
            
            db.session.commit()
            print("✅ Sample data created")
        except Exception as e:
            print(f"⚠️ Sample data may already exist: {e}")
            db.session.rollback()
        
        print("\n✅ ✅ ✅ Permissions system fully initialized!")
        print("\n📋 Next steps:")
        print("1. Access the application")
        print("2. Login with rafael6250@gmail.com")
        print("3. Navigate to /permissions/hierarchical-manager")
        print("4. Use 'Escanear Módulos' button to auto-detect system modules")

if __name__ == "__main__":
    initialize_permissions()