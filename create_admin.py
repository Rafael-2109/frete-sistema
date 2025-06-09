#!/usr/bin/env python3
"""
Script para criar usuário administrador na produção
"""
import os
from datetime import datetime

def create_admin_user():
    try:
        print("=== CRIANDO USUÁRIO ADMINISTRADOR ===")
        
        from app import create_app, db
        from app.auth.models import Usuario
        from werkzeug.security import generate_password_hash
        
        app = create_app()
        
        with app.app_context():
            # Verificar se já existe um administrador
            admin_exists = Usuario.query.filter_by(perfil='administrador').first()
            
            if admin_exists:
                print(f"✓ Administrador já existe: {admin_exists.email}")
                return True
                
            # Criar usuário administrador
            admin_user = Usuario(
                nome='Rafael de Carvalho Nascimento',
                email='rafael@nacomgoya.com.br',
                senha_hash=generate_password_hash('Rafa2109'),
                perfil='administrador',
                status='ativo',
                empresa='NACOM GOYA',
                cargo='Diretor',
                criado_em=datetime.utcnow()
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✓ Usuário administrador criado: {admin_user.email}")
            print("✓ Senha: Rafa2109")
            return True
            
    except Exception as e:
        print(f"❌ ERRO ao criar administrador: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_admin_user() 