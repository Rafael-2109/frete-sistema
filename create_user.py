#!/usr/bin/env python3
"""Script para criar usuário no sistema"""
import sys
from app import create_app, db
from app.auth.models import Usuario

def criar_usuario():
    """Criar novo usuário"""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se usuário já existe
            usuario_existente = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
            if usuario_existente:
                print("❌ Usuário já existe!")
                print(f"   Email: {usuario_existente.email}")
                print(f"   Status: {usuario_existente.status}")
                print(f"   Perfil: {usuario_existente.perfil}")
                return
            
            # Criar novo usuário
            novo_usuario = Usuario(
                nome='Rafael',
                email='rafael6250@gmail.com',
                perfil='administrador',  # Perfil administrador para acesso total
                status='ativo',  # Já ativo para não precisar aprovação
                empresa='NACOM GOYA',
                cargo='Administrador'
            )
            
            # Definir senha
            novo_usuario.set_senha('rafa2109')
            
            # Salvar no banco
            db.session.add(novo_usuario)
            db.session.commit()
            
            print("✅ Usuário criado com sucesso!")
            print(f"   Email: {novo_usuario.email}")
            print(f"   Senha: rafa2109")
            print(f"   Perfil: {novo_usuario.perfil}")
            print(f"   Status: {novo_usuario.status}")
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    criar_usuario()