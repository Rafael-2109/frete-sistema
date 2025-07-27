#!/usr/bin/env python
"""
Script para definir um usuário como admin
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.auth.models import Usuario
from app.permissions.models import PerfilUsuario

def set_user_as_admin(email):
    """Define um usuário como admin"""
    app = create_app()
    
    with app.app_context():
        # Buscar o usuário
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            print(f"❌ Usuário com email {email} não encontrado!")
            return False
            
        # Buscar o perfil admin
        perfil_admin = PerfilUsuario.query.filter_by(nome='admin').first()
        
        if not perfil_admin:
            print("⚠️ Perfil admin não encontrado. Criando...")
            perfil_admin = PerfilUsuario(
                nome='admin',
                nome_exibicao='Administrador',
                descricao='Acesso total ao sistema',
                nivel=10,
                ativo=True
            )
            db.session.add(perfil_admin)
            db.session.commit()
            print("✅ Perfil admin criado!")
        
        # Atualizar o usuário
        usuario.perfil_id = perfil_admin.id
        usuario.perfil_nome = 'admin'
        db.session.commit()
        
        print(f"✅ Usuário {usuario.nome} ({email}) agora é administrador!")
        print(f"   - ID: {usuario.id}")
        print(f"   - Perfil: {perfil_admin.nome_exibicao}")
        print(f"   - Nível: {perfil_admin.nivel}")
        
        return True

if __name__ == "__main__":
    email = "rafael6250@gmail.com"
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    
    print(f"🔧 Configurando usuário {email} como admin...")
    
    if set_user_as_admin(email):
        print("\n🎉 Sucesso! O usuário agora tem acesso total ao sistema.")
        print("📌 Acesse /permissions/admin para gerenciar permissões.")
    else:
        print("\n❌ Erro ao configurar usuário como admin.")