#!/usr/bin/env python3
"""
Script para atualizar registros existentes da portaria no Render
com campos de auditoria usando usuário Rafael de Carvalho Nascimento
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Configuração para o ambiente Render
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Importa os modelos necessários
from app.auth.models import Usuario
from app.portaria.models import ControlePortaria

def atualizar_registros_portaria():
    """Atualiza registros existentes da portaria com usuário padrão"""
    
    with app.app_context():
        try:
            print("🔄 Iniciando atualização dos registros da portaria...")
            
            # 1. Busca ou cria usuário "Rafael de Carvalho Nascimento"
            usuario_rafael = Usuario.query.filter_by(nome='Rafael de Carvalho Nascimento').first()
            
            if not usuario_rafael:
                print("👤 Criando usuário Rafael de Carvalho Nascimento...")
                usuario_rafael = Usuario(
                    nome='Rafael de Carvalho Nascimento',
                    email='rafael.admin@sistema.com',
                    perfil='administrador',
                    status='ativo'
                )
                usuario_rafael.set_senha('admin123')  # Senha temporária
                db.session.add(usuario_rafael)
                db.session.commit()
                print(f"✅ Usuário criado com ID: {usuario_rafael.id}")
            else:
                print(f"👤 Usuário encontrado com ID: {usuario_rafael.id}")
            
            # 2. Verifica se os campos de auditoria existem na tabela
            try:
                # Tenta fazer uma query que usa os campos novos
                teste_campos = db.session.execute(
                    "SELECT registrado_por_id, atualizado_por_id FROM controle_portaria LIMIT 1"
                ).fetchone()
                print("✅ Campos de auditoria já existem na tabela")
                
                # 3. Atualiza registros que têm campos nulos
                registros_atualizados = db.session.execute(
                    f"""UPDATE controle_portaria 
                        SET registrado_por_id = {usuario_rafael.id}, 
                            atualizado_por_id = {usuario_rafael.id}
                        WHERE registrado_por_id IS NULL 
                           OR atualizado_por_id IS NULL"""
                ).rowcount
                
                db.session.commit()
                print(f"✅ {registros_atualizados} registros da portaria atualizados com sucesso!")
                
            except Exception as e:
                if "no such column" in str(e).lower():
                    print("⚠️ Campos de auditoria ainda não existem. Execute a migração primeiro:")
                    print("   flask db upgrade")
                else:
                    print(f"❌ Erro ao verificar campos: {e}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Erro durante a atualização: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 Script de atualização da portaria para o Render")
    print("=" * 50)
    
    success = atualizar_registros_portaria()
    
    if success:
        print("\n✅ Atualização concluída com sucesso!")
        print("🎯 Próximos passos:")
        print("   1. Este script pode ser executado no Render via Web Service")
        print("   2. Ou incluído no processo de deploy automático")
        sys.exit(0)
    else:
        print("\n❌ Atualização falhou!")
        sys.exit(1) 