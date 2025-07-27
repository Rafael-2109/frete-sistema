#!/usr/bin/env python
"""
Script rápido para definir usuário como admin
"""
import os
import sys

# Configurar para não mostrar logs desnecessários
os.environ['SKIP_CLAUDE_AI'] = 'true'
import logging
logging.basicConfig(level=logging.ERROR)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.auth.models import Usuario
from app.permissions.models import PerfilUsuario

app = create_app()

with app.app_context():
    # Buscar ou criar perfil admin
    perfil_admin = PerfilUsuario.query.filter_by(nome='admin').first()
    if not perfil_admin:
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
    
    # Buscar usuário
    usuario = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
    
    if usuario:
        # Atualizar para admin
        usuario.perfil_id = perfil_admin.id
        usuario.perfil_nome = 'admin'
        db.session.commit()
        
        print(f"✅ Usuário {usuario.nome} agora é ADMINISTRADOR!")
        print(f"   Email: {usuario.email}")
        print(f"   Perfil: {perfil_admin.nome_exibicao}")
        print("\n🎉 Acesse /permissions/admin para gerenciar permissões!")
    else:
        print("❌ Usuário rafael6250@gmail.com não encontrado!")