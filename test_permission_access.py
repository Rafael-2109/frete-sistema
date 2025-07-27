#!/usr/bin/env python
"""
Test Permission Access - Quick Test
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Disable Claude AI during test
os.environ['SKIP_CLAUDE_AI'] = 'true'

from app import create_app, db
from app.auth.models import Usuario

def test_permission_access():
    """Test if admin user can access permissions"""
    app = create_app()
    
    with app.app_context():
        # Check user
        user = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
        if not user:
            print("❌ User not found!")
            return
        
        print(f"✅ User found: {user.email}")
        print(f"   - Perfil: {user.perfil}")
        print(f"   - Perfil Nome: {getattr(user, 'perfil_nome', 'N/A')}")
        print(f"   - Status: {user.status}")
        print(f"   - Admin: {user.is_admin}")
        
        # Check if perfil is 'administrador'
        if user.perfil == 'administrador':
            print("✅ User has administrador profile - should have full access!")
        else:
            print(f"⚠️ User profile is '{user.perfil}' not 'administrador'")
        
        # Check permission
        from app.permissions.decorators_simple import require_permission
        print("\n📋 Testing decorator import...")
        print(f"   - Decorator imported successfully")
        
        # Simulate the decorator check
        print("\n🔍 Simulating permission check...")
        print(f"   - Module: permissions")
        print(f"   - Function: gerenciar") 
        print(f"   - Action: editar")
        
        # Check if bypass would work
        if hasattr(user, 'perfil_nome') and user.perfil_nome in ['admin', 'administrador', 'administrator']:
            print("✅ Admin bypass would work!")
        elif user.perfil in ['administrador', 'admin', 'gerente']:
            print("✅ Fallback admin check would work!")
        else:
            print("❌ Permission would be denied!")

if __name__ == "__main__":
    test_permission_access()