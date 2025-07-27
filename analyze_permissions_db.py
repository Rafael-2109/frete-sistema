#!/usr/bin/env python3
"""
Database Permissions Analysis Script
Analyzes the database structure and checks for user permissions
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text
from app.auth.models import Usuario
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    Vendedor, EquipeVendas, UsuarioVendedor, UsuarioEquipeVendas,
    PermissaoVendedor, PermissaoEquipe, LogPermissao,
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate
)

def analyze_database():
    """Analyze database structure and permissions"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("DATABASE PERMISSIONS ANALYSIS")
        print("=" * 80)
        print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        print(f"Timestamp: {datetime.now()}")
        print("=" * 80)
        
        # Get database inspector
        inspector = inspect(db.engine)
        
        # 1. Check table structures
        print("\n1. CHECKING TABLE STRUCTURES")
        print("-" * 40)
        
        tables_to_check = [
            'usuarios', 'perfil_usuario', 'modulo_sistema', 'funcao_modulo',
            'permissao_usuario', 'vendedor', 'equipe_vendas', 'usuario_vendedor',
            'usuario_equipe_vendas', 'permissao_vendedor', 'permissao_equipe',
            'log_permissao', 'permission_category', 'permission_module',
            'permission_submodule', 'user_permission', 'permission_template'
        ]
        
        existing_tables = inspector.get_table_names()
        
        for table in tables_to_check:
            if table in existing_tables:
                columns = inspector.get_columns(table)
                print(f"\n✅ Table '{table}' exists with {len(columns)} columns:")
                for col in columns[:5]:  # Show first 5 columns
                    print(f"   - {col['name']} ({col['type']})")
                if len(columns) > 5:
                    print(f"   ... and {len(columns) - 5} more columns")
            else:
                print(f"\n❌ Table '{table}' NOT FOUND")
        
        # 2. Check for specific user
        print("\n\n2. CHECKING USER: rafael6250@gmail.com")
        print("-" * 40)
        
        user = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
        
        if user:
            print(f"✅ User found:")
            print(f"   - ID: {user.id}")
            print(f"   - Nome: {user.nome}")
            print(f"   - Email: {user.email}")
            print(f"   - Perfil: {user.perfil}")
            print(f"   - Status: {user.status}")
            print(f"   - Empresa: {user.empresa}")
            print(f"   - Criado em: {user.criado_em}")
            print(f"   - Último login: {user.ultimo_login}")
            
            # Check if user is admin
            if user.perfil == 'administrador':
                print(f"\n   🎯 USER HAS ADMINISTRATOR PROFILE!")
            else:
                print(f"\n   ⚠️  User profile is '{user.perfil}', not 'administrador'")
            
            # Check permissions
            print(f"\n   Checking permissions:")
            
            # Check new permission system
            permissions = PermissaoUsuario.query.filter_by(usuario_id=user.id, ativo=True).all()
            if permissions:
                print(f"   - Found {len(permissions)} active permissions in new system")
                for perm in permissions[:5]:
                    print(f"     • {perm.funcao.modulo.nome}.{perm.funcao.nome}: View={perm.pode_visualizar}, Edit={perm.pode_editar}")
            else:
                print(f"   - No permissions found in new system")
            
            # Check hierarchical permissions
            user_perms = UserPermission.query.filter_by(user_id=user.id, active=True).all()
            if user_perms:
                print(f"   - Found {len(user_perms)} hierarchical permissions")
            else:
                print(f"   - No hierarchical permissions found")
            
            # Check vendedor associations
            vendedores = UsuarioVendedor.query.filter_by(usuario_id=user.id, ativo=True).all()
            if vendedores:
                print(f"   - Associated with {len(vendedores)} vendedor(es)")
            
            # Check equipe associations
            equipes = UsuarioEquipeVendas.query.filter_by(usuario_id=user.id, ativo=True).all()
            if equipes:
                print(f"   - Associated with {len(equipes)} equipe(s)")
                
        else:
            print("❌ User NOT FOUND in database")
        
        # 3. Check permission_category table structure
        print("\n\n3. ANALYZING PERMISSION_CATEGORY TABLE")
        print("-" * 40)
        
        if 'permission_category' in existing_tables:
            # Get column details
            columns = inspector.get_columns('permission_category')
            print("Column structure:")
            for col in columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                print(f"   - {col['name']}: {col['type']} {nullable}")
            
            # Check data
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM permission_category"))
                count = result.scalar()
                print(f"\nRow count: {count}")
                
                if count > 0:
                    result = db.session.execute(text("SELECT * FROM permission_category LIMIT 5"))
                    rows = result.fetchall()
                    print("\nSample data:")
                    for row in rows:
                        print(f"   - {dict(row._mapping)}")
            except Exception as e:
                print(f"Error querying permission_category: {e}")
        
        # 4. Check all admin users
        print("\n\n4. ALL ADMINISTRATOR USERS")
        print("-" * 40)
        
        admins = Usuario.query.filter_by(perfil='administrador').all()
        if admins:
            print(f"Found {len(admins)} administrator(s):")
            for admin in admins:
                print(f"   - {admin.email} (Status: {admin.status})")
        else:
            print("❌ No administrators found")
        
        # 5. Check perfil_usuario table
        print("\n\n5. CHECKING PERFIL_USUARIO DATA")
        print("-" * 40)
        
        perfis = PerfilUsuario.query.all()
        if perfis:
            print(f"Found {len(perfis)} profiles:")
            for perfil in perfis:
                print(f"   - {perfil.nome}: {perfil.descricao} (Nível: {perfil.nivel_hierarquico})")
        else:
            print("❌ No profiles found in perfil_usuario table")
        
        # 6. Check modules and functions
        print("\n\n6. MODULES AND FUNCTIONS")
        print("-" * 40)
        
        modulos = ModuloSistema.query.filter_by(ativo=True).all()
        if modulos:
            print(f"Found {len(modulos)} active modules:")
            for modulo in modulos:
                funcoes_count = FuncaoModulo.query.filter_by(modulo_id=modulo.id, ativo=True).count()
                print(f"   - {modulo.nome} ({modulo.nome_exibicao}): {funcoes_count} functions")
        else:
            print("❌ No active modules found")
        
        # 7. Check for data discrepancies
        print("\n\n7. CHECKING FOR DISCREPANCIES")
        print("-" * 40)
        
        # Check if usuario table has expected columns
        usuario_columns = {col['name'] for col in inspector.get_columns('usuarios')}
        expected_columns = {'id', 'nome', 'email', 'senha_hash', 'perfil', 'status'}
        missing_columns = expected_columns - usuario_columns
        
        if missing_columns:
            print(f"⚠️  Missing columns in usuarios table: {missing_columns}")
        else:
            print("✅ All expected columns present in usuarios table")
        
        # Check foreign key references
        print("\nChecking foreign key integrity...")
        
        # Check if all PermissaoUsuario entries have valid usuario_id
        try:
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM permissao_usuario p
                LEFT JOIN usuarios u ON p.usuario_id = u.id
                WHERE u.id IS NULL
            """))
            orphaned = result.scalar()
            if orphaned > 0:
                print(f"⚠️  Found {orphaned} orphaned permission entries")
            else:
                print("✅ All permissions have valid user references")
        except Exception as e:
            print(f"Error checking foreign keys: {e}")
        
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    analyze_database()