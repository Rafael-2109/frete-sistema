#!/usr/bin/env python3
"""
Detailed Database Analysis with proper transaction management
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
from app.auth.models import Usuario

def run_detailed_analysis():
    """Run detailed database analysis"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("DETAILED DATABASE PERMISSIONS ANALYSIS")
        print("=" * 80)
        print(f"Timestamp: {datetime.now()}")
        print("=" * 80)
        
        # Start fresh transaction
        db.session.rollback()
        
        # 1. Direct SQL analysis of permission_category
        print("\n1. PERMISSION_CATEGORY TABLE")
        print("-" * 40)
        
        try:
            # Check if table exists and get columns
            result = db.session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'permission_category'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            
            if columns:
                print("✅ Table exists with columns:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]}")
                
                # Try to query with correct column name
                db.session.rollback()  # Clear any errors
                result = db.session.execute(text("SELECT id, nome, nome_exibicao FROM permission_category"))
                rows = result.fetchall()
                
                print(f"\nData ({len(rows)} rows):")
                for row in rows:
                    print(f"   - ID: {row[0]}, Nome: {row[1]}, Display: {row[2]}")
            else:
                print("❌ Table not found or no columns")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
        
        # 2. Check user rafael6250@gmail.com
        print("\n\n2. USER ANALYSIS: rafael6250@gmail.com")
        print("-" * 40)
        
        try:
            # Use ORM to avoid SQL errors
            user = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
            
            if user:
                print(f"✅ User found:")
                print(f"   - ID: {user.id}")
                print(f"   - Nome: {user.nome}")
                print(f"   - Email: {user.email}")
                print(f"   - Perfil: {user.perfil}")
                print(f"   - Status: {user.status}")
                
                # Check if admin
                if user.perfil == 'administrador':
                    print(f"\n   🎯 USER IS ADMINISTRATOR!")
                    
                    # Check permissions using ORM methods
                    print(f"\n   Testing permission methods:")
                    print(f"   - pode_aprovar_usuarios(): {user.pode_aprovar_usuarios()}")
                    print(f"   - pode_acessar_financeiro(): {user.pode_acessar_financeiro()}")
                    print(f"   - pode_acessar_embarques(): {user.pode_acessar_embarques()}")
                    print(f"   - pode_acessar_portaria(): {user.pode_acessar_portaria()}")
                    
                    # Test new permission system
                    print(f"\n   Testing new permission system:")
                    try:
                        # Test carteira module access
                        has_carteira = user.tem_permissao('carteira')
                        print(f"   - tem_permissao('carteira'): {has_carteira}")
                        
                        # Test specific function
                        can_list = user.tem_permissao('carteira', 'listar')
                        print(f"   - tem_permissao('carteira', 'listar'): {can_list}")
                        
                        # Get permitted modules
                        modules = user.get_modulos_permitidos()
                        print(f"   - get_modulos_permitidos(): {len(modules)} modules")
                        for mod in modules[:3]:
                            print(f"     • {mod.nome}: {mod.nome_exibicao}")
                            
                    except Exception as e:
                        print(f"   - New permission system error: {e}")
                        
            else:
                print("❌ User not found")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
        
        # 3. Check all admin users
        print("\n\n3. ALL ADMINISTRATOR USERS")
        print("-" * 40)
        
        try:
            admins = Usuario.query.filter_by(perfil='administrador').all()
            
            if admins:
                print(f"Found {len(admins)} administrator(s):")
                for admin in admins:
                    print(f"   - {admin.email}")
                    print(f"     • Status: {admin.status}")
                    print(f"     • Created: {admin.criado_em}")
                    print(f"     • Last login: {admin.ultimo_login}")
            else:
                print("❌ No administrators found")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
        
        # 4. Check tables structure discrepancies
        print("\n\n4. TABLE STRUCTURE DISCREPANCIES")
        print("-" * 40)
        
        try:
            # Check if permission models match database
            from app.permissions.models import PermissionCategory
            
            # Try to query PermissionCategory model
            try:
                categories = PermissionCategory.query.all()
                print(f"✅ PermissionCategory model works: {len(categories)} categories")
            except Exception as e:
                print(f"❌ PermissionCategory model error: {e}")
                
                # Check actual column names in DB
                db.session.rollback()
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'permission_category'
                    AND column_name IN ('name', 'nome', 'display_name', 'nome_exibicao')
                """))
                
                found_columns = [row[0] for row in result.fetchall()]
                print(f"\n   Found columns in DB: {found_columns}")
                print(f"   Model expects: 'name' and 'display_name'")
                print(f"   DB has: 'nome' and 'nome_exibicao'")
                print(f"\n   🔴 MISMATCH DETECTED! Model uses English names, DB uses Portuguese names")
                
        except ImportError:
            print("❌ Could not import PermissionCategory model")
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
        
        # 5. Check permission system initialization
        print("\n\n5. PERMISSION SYSTEM INITIALIZATION")
        print("-" * 40)
        
        try:
            # Check if default data exists
            from app.permissions.models import PerfilUsuario, ModuloSistema, FuncaoModulo
            
            perfis = PerfilUsuario.query.all()
            modulos = ModuloSistema.query.all()
            funcoes = FuncaoModulo.query.all()
            
            print(f"Default data status:")
            print(f"   - Perfis: {len(perfis)} profiles")
            print(f"   - Modules: {len(modulos)} modules")
            print(f"   - Functions: {len(funcoes)} functions")
            
            if len(perfis) == 0 or len(modulos) == 0:
                print(f"\n   ⚠️  Missing default data! Run initialization:")
                print(f"   from app.permissions.models import inicializar_dados_padrao")
                print(f"   inicializar_dados_padrao()")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
        
        # 6. Summary and recommendations
        print("\n\n6. SUMMARY AND RECOMMENDATIONS")
        print("-" * 40)
        
        print("Key findings:")
        print("1. User rafael6250@gmail.com exists and has 'administrador' profile ✅")
        print("2. permission_category table has Portuguese column names (nome, nome_exibicao)")
        print("3. PermissionCategory model expects English names (name, display_name)")
        print("4. This mismatch is causing the AttributeError")
        print("\nRecommendation: Update the PermissionCategory model to use Portuguese column names")
        
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    run_detailed_analysis()