#!/usr/bin/env python3
"""
SQL-based Permissions Analysis
Direct SQL queries to analyze permissions database
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def run_sql_analysis():
    """Run SQL analysis on permissions database"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("SQL PERMISSIONS ANALYSIS")
        print("=" * 80)
        print(f"Timestamp: {datetime.now()}")
        print("=" * 80)
        
        # 1. Check permission_category structure and data
        print("\n1. PERMISSION_CATEGORY TABLE ANALYSIS")
        print("-" * 40)
        
        try:
            # Check column structure
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'permission_category'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            
            print("Column structure:")
            for col in columns:
                print(f"   - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
            
            # Check data
            result = db.session.execute(text("SELECT * FROM permission_category"))
            categories = result.fetchall()
            
            print(f"\nData ({len(categories)} rows):")
            for cat in categories:
                print(f"   - ID: {cat[0]}, Nome: {cat[1]}, Display: {cat[2]}")
                
        except Exception as e:
            print(f"Error analyzing permission_category: {e}")
        
        # 2. Check if permission_category has correct columns
        print("\n\n2. CHECKING COLUMN NAMES")
        print("-" * 40)
        
        try:
            # Try different column name variations
            queries = [
                ("name", "SELECT name FROM permission_category LIMIT 1"),
                ("nome", "SELECT nome FROM permission_category LIMIT 1"),
                ("display_name", "SELECT display_name FROM permission_category LIMIT 1"),
                ("nome_exibicao", "SELECT nome_exibicao FROM permission_category LIMIT 1"),
            ]
            
            for col_name, query in queries:
                try:
                    result = db.session.execute(text(query))
                    result.fetchone()
                    print(f"✅ Column '{col_name}' exists in permission_category")
                except Exception as e:
                    print(f"❌ Column '{col_name}' NOT found: {str(e).split('DETAIL')[0]}")
                    
        except Exception as e:
            print(f"Error checking columns: {e}")
        
        # 3. Check usuarios table permissions columns
        print("\n\n3. USUARIOS TABLE PERMISSIONS ANALYSIS")
        print("-" * 40)
        
        try:
            # Check rafael6250@gmail.com permissions
            result = db.session.execute(text("""
                SELECT u.id, u.nome, u.email, u.perfil, u.status,
                       COUNT(DISTINCT pu.id) as permission_count
                FROM usuarios u
                LEFT JOIN permissao_usuario pu ON u.id = pu.usuario_id AND pu.ativo = true
                WHERE u.email = 'rafael6250@gmail.com'
                GROUP BY u.id, u.nome, u.email, u.perfil, u.status
            """))
            
            user_data = result.fetchone()
            if user_data:
                print(f"User details:")
                print(f"   - ID: {user_data[0]}")
                print(f"   - Nome: {user_data[1]}")
                print(f"   - Email: {user_data[2]}")
                print(f"   - Perfil: {user_data[3]}")
                print(f"   - Status: {user_data[4]}")
                print(f"   - Active permissions: {user_data[5]}")
            
        except Exception as e:
            print(f"Error analyzing user: {e}")
        
        # 4. Check all tables with 'permission' in name
        print("\n\n4. ALL PERMISSION-RELATED TABLES")
        print("-" * 40)
        
        try:
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND (table_name LIKE '%permission%' OR table_name LIKE '%permiss%')
                ORDER BY table_name
            """))
            
            tables = result.fetchall()
            print(f"Found {len(tables)} permission-related tables:")
            for table in tables:
                # Get row count
                count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table[0]}"))
                count = count_result.scalar()
                print(f"   - {table[0]}: {count} rows")
                
        except Exception as e:
            print(f"Error listing permission tables: {e}")
        
        # 5. Check modulo_sistema and funcao_modulo data
        print("\n\n5. MODULES AND FUNCTIONS ANALYSIS")
        print("-" * 40)
        
        try:
            # Count modules
            result = db.session.execute(text("SELECT COUNT(*) FROM modulo_sistema WHERE ativo = true"))
            module_count = result.scalar()
            print(f"Active modules: {module_count}")
            
            # List modules with function count
            result = db.session.execute(text("""
                SELECT m.nome, m.nome_exibicao, COUNT(f.id) as func_count
                FROM modulo_sistema m
                LEFT JOIN funcao_modulo f ON m.id = f.modulo_id AND f.ativo = true
                WHERE m.ativo = true
                GROUP BY m.id, m.nome, m.nome_exibicao
                ORDER BY m.ordem
            """))
            
            modules = result.fetchall()
            print("\nModules and their functions:")
            for mod in modules:
                print(f"   - {mod[0]} ({mod[1]}): {mod[2]} functions")
                
        except Exception as e:
            print(f"Error analyzing modules: {e}")
        
        # 6. Check for admin permissions setup
        print("\n\n6. ADMIN PERMISSIONS SETUP")
        print("-" * 40)
        
        try:
            # Check if any admin has permissions
            result = db.session.execute(text("""
                SELECT u.email, COUNT(pu.id) as perm_count
                FROM usuarios u
                LEFT JOIN permissao_usuario pu ON u.id = pu.usuario_id AND pu.ativo = true
                WHERE u.perfil = 'administrador' AND u.status = 'ativo'
                GROUP BY u.id, u.email
            """))
            
            admins = result.fetchall()
            print("Administrator permissions:")
            for admin in admins:
                print(f"   - {admin[0]}: {admin[1]} explicit permissions")
                
            # Check if admin profile exists in perfil_usuario
            result = db.session.execute(text("""
                SELECT nome, descricao, nivel_hierarquico
                FROM perfil_usuario
                WHERE nome = 'administrador'
            """))
            
            admin_profile = result.fetchone()
            if admin_profile:
                print(f"\nAdmin profile in perfil_usuario:")
                print(f"   - Nome: {admin_profile[0]}")
                print(f"   - Descrição: {admin_profile[1]}")
                print(f"   - Nível: {admin_profile[2]}")
            else:
                print("\n❌ No 'administrador' profile found in perfil_usuario table")
                
        except Exception as e:
            print(f"Error checking admin setup: {e}")
        
        # 7. Check templates
        print("\n\n7. PERMISSION TEMPLATES")
        print("-" * 40)
        
        try:
            result = db.session.execute(text("""
                SELECT nome, descricao, perfil_id
                FROM permission_template
                WHERE ativo = true
            """))
            
            templates = result.fetchall()
            print(f"Found {len(templates)} active templates:")
            for tmpl in templates:
                print(f"   - {tmpl[0]}: {tmpl[1]} (perfil_id: {tmpl[2]})")
                
        except Exception as e:
            print(f"Error checking templates: {e}")
        
        print("\n" + "=" * 80)
        print("SQL ANALYSIS COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    run_sql_analysis()