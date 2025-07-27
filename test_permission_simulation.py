#!/usr/bin/env python
"""
Simulate the exact permission check for hierarchical-manager route
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Disable Claude AI during test
os.environ['SKIP_CLAUDE_AI'] = 'true'

from app import create_app, db
from app.auth.models import Usuario
from flask import g
from werkzeug.test import Client
from werkzeug.serving import WSGIRequestHandler

def test_route_access():
    """Test accessing the hierarchical-manager route"""
    app = create_app()
    
    with app.app_context():
        # Get user
        user = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
        if not user:
            print("❌ User not found!")
            return
        
        print(f"✅ User found: {user.email}")
        print(f"   - Perfil: {user.perfil}")
        print(f"   - Perfil Nome: {getattr(user, 'perfil_nome', 'N/A')}")
        print(f"   - Is Admin: {getattr(user, 'is_admin', False)}")
        
        # Test with Flask test client
        with app.test_client() as client:
            # Login the user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Try to access the route
            print("\n🔍 Testing route access...")
            response = client.get('/permissions/hierarchical-manager')
            
            print(f"📋 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ ✅ ✅ ACESSO PERMITIDO! O ERRO FOI RESOLVIDO!")
            elif response.status_code == 302:
                print(f"🔄 Redirecionamento para: {response.location}")
                if 'login' in response.location:
                    print("❌ Redirecionado para login (não autenticado)")
                else:
                    print("❌ Redirecionado (sem permissão)")
            elif response.status_code == 403:
                print("❌ ❌ ❌ ERRO 403 AINDA PERSISTE!")
                print("\n📝 VERIFICAÇÕES NECESSÁRIAS:")
                print("1. O decorator está verificando perfil_nome corretamente?")
                print("2. O current_user está sendo carregado com todos os atributos?")
                print("3. Há algum middleware interceptando?")
            else:
                print(f"⚠️ Status inesperado: {response.status_code}")
            
            # Check if we got flash messages
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
                if flashes:
                    print("\n💬 Flash Messages:")
                    for category, message in flashes:
                        print(f"   [{category}] {message}")

if __name__ == "__main__":
    test_route_access()