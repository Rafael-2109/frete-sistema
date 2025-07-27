#!/usr/bin/env python
"""
Test Permission Access - Final Version
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
        
        # Check if perfil is 'administrador'
        if user.perfil == 'administrador':
            print("✅ User has administrador profile - should have full access!")
        else:
            print(f"⚠️ User profile is '{user.perfil}' not 'administrador'")
        
        # Check decorators
        print("\n📋 Testing decorator behavior...")
        
        # Check if bypass would work with perfil_nome
        perfil_nome = getattr(user, 'perfil_nome', None)
        if perfil_nome and perfil_nome in ['admin', 'administrador', 'administrator', 'Administrador']:
            print(f"✅ Admin bypass would work! perfil_nome='{perfil_nome}' is in allowed list")
        else:
            print(f"❌ Admin bypass would NOT work! perfil_nome='{perfil_nome}' is not in allowed list")
            
        # Check if bypass would work with perfil
        if user.perfil in ['administrador', 'admin', 'gerente']:
            print(f"✅ Fallback admin check would work! perfil='{user.perfil}' is in allowed list")
        else:
            print(f"❌ Fallback would NOT work! perfil='{user.perfil}' is not in allowed list")

        print("\n🔍 RESULTADO FINAL:")
        if (perfil_nome and perfil_nome in ['admin', 'administrador', 'administrator', 'Administrador']) or \
           (user.perfil in ['administrador', 'admin', 'gerente']):
            print("✅ ✅ ✅ O USUÁRIO DEVERIA TER ACESSO TOTAL!")
            print("Se ainda recebe 403, verificar:")
            print("1. Se o decorator correto está sendo importado")
            print("2. Se não há cache/sessão antiga")
            print("3. Se o perfil_nome está sendo carregado corretamente")
        else:
            print("❌ ❌ ❌ O USUÁRIO NÃO TEM PERMISSÃO!")

if __name__ == "__main__":
    test_permission_access()