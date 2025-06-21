#!/usr/bin/env python3
"""
🔐 CRIAR USUÁRIO ADMINISTRADOR
Script para criar um usuário administrador no sistema de fretes
"""

import os
import sys
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def criar_usuario_admin():
    """Cria um usuário administrador"""
    
    try:
        # Importar módulos do Flask
        from app import create_app, db
        from app.auth.models import Usuario
        
        print("🚀 CRIANDO USUÁRIO ADMINISTRADOR")
        print("=" * 50)
        
        # Criar contexto da aplicação
        app = create_app()
        
        with app.app_context():
            print("📊 Verificando usuários existentes...")
            
            # Verificar se já existe admin
            admin_existente = Usuario.query.filter_by(perfil='administrador').first()
            if admin_existente:
                print(f"⚠️  Já existe um administrador: {admin_existente.email}")
                
                if input("Deseja criar outro admin? (s/N): ").lower() not in ['s', 'sim', 'y', 'yes']:
                    print("❌ Operação cancelada.")
                    return False
            
            # Dados do usuário
            print("\n📝 Digite os dados do administrador:")
            
            nome = input("Nome completo: ").strip()
            if not nome:
                print("❌ Nome é obrigatório!")
                return False
            
            email = input("Email: ").strip().lower()
            if not email or '@' not in email:
                print("❌ Email válido é obrigatório!")
                return False
            
            # Verificar se email já existe
            usuario_existente = Usuario.query.filter_by(email=email).first()
            if usuario_existente:
                print(f"❌ Email {email} já está em uso!")
                return False
            
            senha = input("Senha: ").strip()
            if not senha or len(senha) < 6:
                print("❌ Senha deve ter pelo menos 6 caracteres!")
                return False
            
            confirma_senha = input("Confirme a senha: ").strip()
            if senha != confirma_senha:
                print("❌ Senhas não conferem!")
                return False
            
            empresa = input("Empresa (opcional): ").strip() or "Sistema de Fretes"
            cargo = input("Cargo (opcional): ").strip() or "Administrador do Sistema"
            telefone = input("Telefone (opcional): ").strip()
            
            print("\n🔧 Criando usuário...")
            
            # Criar usuário
            novo_admin = Usuario(
                nome=nome,
                email=email,
                perfil='administrador',
                status='ativo',  # Admin já começa ativo
                empresa=empresa,
                cargo=cargo,
                telefone=telefone,
                criado_em=datetime.utcnow(),
                aprovado_em=datetime.utcnow(),
                aprovado_por='Sistema'  # Auto-aprovado
            )
            
            # Definir senha
            novo_admin.set_senha(senha)
            
            # Salvar no banco
            db.session.add(novo_admin)
            db.session.commit()
            
            print("✅ Usuário administrador criado com sucesso!")
            print("=" * 50)
            print(f"📧 Email: {email}")
            print(f"👤 Nome: {nome}")
            print(f"🏢 Empresa: {empresa}")
            print(f"💼 Cargo: {cargo}")
            print(f"🔑 Perfil: Administrador")
            print(f"✅ Status: Ativo")
            
            if telefone:
                print(f"📱 Telefone: {telefone}")
            
            print("=" * 50)
            print("🌐 Acesse o sistema em: http://localhost:5000")
            print("💬 Claude AI Dashboard: http://localhost:5000/claude-ai/dashboard")
            
            return True
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("💡 Certifique-se de que está no diretório correto e o venv está ativo")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {e}")
        return False

def listar_usuarios():
    """Lista usuários existentes"""
    
    try:
        from app import create_app, db
        from app.auth.models import Usuario
        
        app = create_app()
        
        with app.app_context():
            usuarios = Usuario.query.all()
            
            if not usuarios:
                print("📭 Nenhum usuário encontrado.")
                return
            
            print(f"\n👥 USUÁRIOS CADASTRADOS ({len(usuarios)}):")
            print("-" * 80)
            print(f"{'ID':<5} {'Nome':<25} {'Email':<30} {'Perfil':<15} {'Status':<10}")
            print("-" * 80)
            
            for user in usuarios:
                print(f"{user.id:<5} {user.nome[:24]:<25} {user.email[:29]:<30} {user.perfil_nome:<15} {user.status:<10}")
            
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")

def alterar_senha_usuario():
    """Altera senha de um usuário existente"""
    
    try:
        from app import create_app, db
        from app.auth.models import Usuario
        
        app = create_app()
        
        with app.app_context():
            email = input("Email do usuário: ").strip().lower()
            if not email:
                print("❌ Email é obrigatório!")
                return False
            
            usuario = Usuario.query.filter_by(email=email).first()
            if not usuario:
                print(f"❌ Usuário com email {email} não encontrado!")
                return False
            
            print(f"✅ Usuário encontrado: {usuario.nome} ({usuario.perfil_nome})")
            
            nova_senha = input("Nova senha: ").strip()
            if not nova_senha or len(nova_senha) < 6:
                print("❌ Senha deve ter pelo menos 6 caracteres!")
                return False
            
            confirma_senha = input("Confirme a nova senha: ").strip()
            if nova_senha != confirma_senha:
                print("❌ Senhas não conferem!")
                return False
            
            usuario.set_senha(nova_senha)
            db.session.commit()
            
            print(f"✅ Senha alterada com sucesso para {usuario.email}!")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao alterar senha: {e}")
        return False

def main():
    """Função principal com menu"""
    
    print("🔐 GERENCIADOR DE USUÁRIOS - SISTEMA DE FRETES")
    print("=" * 50)
    
    while True:
        print("\nOpções disponíveis:")
        print("1. Criar usuário administrador")
        print("2. Listar usuários existentes") 
        print("3. Alterar senha de usuário")
        print("4. Sair")
        
        opcao = input("\nEscolha uma opção (1-4): ").strip()
        
        if opcao == '1':
            criar_usuario_admin()
        elif opcao == '2':
            listar_usuarios()
        elif opcao == '3':
            alterar_senha_usuario()
        elif opcao == '4':
            print("👋 Saindo...")
            break
        else:
            print("❌ Opção inválida!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Script interrompido pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        sys.exit(1) 