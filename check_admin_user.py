#!/usr/bin/env python
"""
Script para verificar se um usuário é admin
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.auth.models import Usuario

def check_admin_user(email):
    """Verifica se um usuário é admin"""
    app = create_app()
    
    with app.app_context():
        # Buscar o usuário
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            print(f"❌ Usuário com email {email} não encontrado!")
            return
            
        print(f"📋 Informações do usuário:")
        print(f"   - Nome: {usuario.nome}")
        print(f"   - Email: {usuario.email}")
        print(f"   - ID: {usuario.id}")
        print(f"   - Perfil ID: {usuario.perfil_id}")
        print(f"   - Perfil Nome: {usuario.perfil_nome}")
        print(f"   - Status: {usuario.status}")
        print(f"   - Criado em: {usuario.criado_em}")
        
        if usuario.perfil_nome == 'admin':
            print("\n✅ Este usuário É ADMINISTRADOR!")
        else:
            print(f"\n⚠️ Este usuário NÃO é administrador (perfil atual: {usuario.perfil_nome or 'nenhum'})")

if __name__ == "__main__":
    email = "rafael6250@gmail.com"
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    
    check_admin_user(email)