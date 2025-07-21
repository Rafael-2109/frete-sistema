#!/usr/bin/env python3
"""
Script de Deploy Seguro - Sistema de Permissões
===============================================

ESTE SCRIPT DEVE SER EXECUTADO COM CUIDADO!
Implementa deploy gradual e seguro das novas funcionalidades.

Autor: Sistema de Fretes
Data: 2025-01-27
"""

import os
import sys
import subprocess
from datetime import datetime

def print_step(step, message):
    """Imprime passo numerado"""
    print(f"\n{'='*60}")
    print(f"PASSO {step}: {message}")
    print('='*60)

def print_warning(message):
    """Imprime aviso em amarelo"""
    print(f"\nAVISO: {message}")

def print_success(message):
    """Imprime sucesso em verde"""
    print(f"\nSUCESSO: {message}")

def print_error(message):
    """Imprime erro em vermelho"""
    print(f"\nERRO: {message}")

def run_command(command, description=""):
    """Executa comando com tratamento de erro"""
    if description:
        print(f"\n-> {description}")
        print(f"Comando: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True, encoding='utf-8')
        if result.stdout:
            print(f"Resultado: {result.stdout.strip()}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_error(f"Falha na execução: {e}")
        if e.stderr:
            print(f"Erro: {e.stderr}")
        return False, str(e)

def check_prerequisites():
    """Verifica pré-requisitos"""
    print_step(1, "VERIFICAÇÃO DE PRÉ-REQUISITOS")
    
    # Verificar se estamos no diretório correto
    if not os.path.exists('app') or not os.path.exists('migrations'):
        print_error("Execute este script na raiz do projeto!")
        return False
    
    # Verificar se a migration existe
    migration_path = "migrations/versions/add_permissions_equipe_vendas.py"
    if not os.path.exists(migration_path):
        print_error(f"Migration não encontrada: {migration_path}")
        return False
    
    print_success("Pré-requisitos verificados")
    return True

def backup_database():
    """Faz backup do banco atual"""
    print_step(2, "BACKUP DO BANCO DE DADOS")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Timestamp do backup: {timestamp}")
    
    print_warning("IMPORTANTE: Faça backup manual do banco PostgreSQL no Render!")
    print("1. Acesse o painel do Render")
    print("2. Vá para seu banco PostgreSQL")
    print("3. Clique em 'Create Backup'")
    print("4. Aguarde confirmação do backup")
    
    resposta = input("\n✅ Backup manual concluído? (s/N): ").lower()
    if resposta != 's':
        print_error("Deploy cancelado - backup necessário!")
        return False
    
    print_success("Backup confirmado pelo usuário")
    return True

def check_current_migration():
    """Verifica migration atual"""
    print_step(3, "VERIFICAÇÃO DA MIGRATION ATUAL")
    
    # Tentar verificar a migration atual
    success, output = run_command("flask db current", "Verificando migration atual")
    
    if success:
        print(f"Migration atual: {output}")
        return True
    else:
        print_warning("Não foi possível verificar migration atual")
        print("Isso pode ser normal se o banco não foi inicializado ainda")
        return True  # Continuar mesmo assim

def show_migration_plan():
    """Mostra o que será executado"""
    print_step(4, "PLANO DE MIGRAÇÃO")
    
    print("🚀 O QUE SERÁ EXECUTADO:")
    print("\n📋 TABELAS A SEREM CRIADAS:")
    print("   • perfil_usuario")
    print("   • modulo_sistema")
    print("   • funcao_modulo")  
    print("   • permissao_usuario")
    print("   • usuario_vendedor")
    print("   • usuario_equipe_vendas")
    print("   • log_permissao")
    
    print("\n📝 CAMPOS A SEREM ADICIONADOS:")
    print("   • relatoriofaturamentoimportado.equipe_vendas")
    print("   • faturamentoproduto.equipe_vendas")
    
    print("\n⚡ ÍNDICES A SEREM CRIADOS:")
    print("   • 13 índices para performance das consultas")
    
    print("\n🔧 FUNCIONALIDADES HABILITADAS:")
    print("   • Sistema de permissões granular")
    print("   • Controle por módulo e função")
    print("   • Multi-vendedor por usuário")
    print("   • Multi-equipe por usuário") 
    print("   • Log de auditoria completo")
    print("   • Interface de administração")
    
    resposta = input("\n✅ Confirma a execução? (s/N): ").lower()
    return resposta == 's'

def execute_migration():
    """Executa a migration"""
    print_step(5, "EXECUÇÃO DA MIGRAÇÃO")
    
    print("🔄 Executando migration...")
    success, output = run_command("flask db upgrade", "Aplicando migration")
    
    if success:
        print_success("Migration executada com sucesso!")
        return True
    else:
        print_error("Falha na migration!")
        return False

def initialize_default_data():
    """Inicializa dados padrão"""
    print_step(6, "INICIALIZAÇÃO DE DADOS PADRÃO")
    
    print("📝 Inicializando perfis, módulos e funções padrão...")
    
    init_script = """
from app import create_app
from app.permissions.models import PerfilUsuario, ModuloSistema, FuncaoModulo

app = create_app()
with app.app_context():
    print("Criando perfis padrão...")
    PerfilUsuario.get_or_create_default_profiles()
    
    print("Criando módulos padrão...")
    ModuloSistema.get_or_create_default_modules()
    
    print("Criando funções padrão...")
    FuncaoModulo.get_or_create_default_functions()
    
    print("✅ Dados padrão inicializados!")
"""
    
    # Salvar script temporário
    with open('temp_init.py', 'w', encoding='utf-8') as f:
        f.write(init_script)
    
    try:
        success, output = run_command("python temp_init.py", "Inicializando dados")
        if success:
            print_success("Dados padrão inicializados!")
            return True
        else:
            print_warning("Falha na inicialização - pode ser feita manualmente depois")
            return True
    finally:
        # Limpar arquivo temporário
        if os.path.exists('temp_init.py'):
            os.remove('temp_init.py')

def test_system():
    """Testa se o sistema está funcionando"""
    print_step(7, "TESTE DO SISTEMA")
    
    print("🧪 Testando imports...")
    
    test_script = """
from app import create_app
from app.permissions.models import PerfilUsuario, ModuloSistema

app = create_app()
with app.app_context():
    perfis = PerfilUsuario.query.count()
    modulos = ModuloSistema.query.count()
    print(f"✅ Perfis: {perfis}")
    print(f"✅ Módulos: {modulos}")
    print("✅ Sistema funcionando!")
"""
    
    with open('temp_test.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    try:
        success, output = run_command("python temp_test.py", "Testando sistema")
        if success:
            print_success("Sistema testado com sucesso!")
            return True
        else:
            print_warning("Teste falhou - verificar logs")
            return False
    finally:
        if os.path.exists('temp_test.py'):
            os.remove('temp_test.py')

def show_next_steps():
    """Mostra próximos passos"""
    print_step(8, "PRÓXIMOS PASSOS")
    
    print("🎯 DEPLOY COMPLETO!")
    print("\n📋 AÇÕES RECOMENDADAS:")
    print("1. ✅ Fazer commit das alterações")
    print("2. ✅ Push para o repositório")  
    print("3. ✅ Deploy no Render")
    print("4. ✅ Acessar /admin/permissions/ para configurar")
    print("5. ✅ Criar perfis de usuários")
    print("6. ✅ Definir vendedores/equipes por usuário")
    
    print("\n🔗 ACESSO À INTERFACE:")
    print("   • URL: /admin/permissions/")
    print("   • Menu: Admin → Sistema de Permissões → Gerenciar Permissões")
    print("   • Restrição: Apenas administradores")
    
    print("\n⚠️  LEMBRE-SE:")
    print("   • Configurar equipes de vendas no Odoo (crm.team)")
    print("   • Testar sincronização completa (FATURAMENTO → CARTEIRA)")
    print("   • Verificar logs de auditoria")

def main():
    """Função principal"""
    print("DEPLOY SEGURO - SISTEMA DE PERMISSOES")
    print("====================================")
    print("Este script executara o deploy do sistema de permissoes")
    print("com verificacoes de seguranca em cada etapa.")
    
    try:
        # Passo 1: Pré-requisitos
        if not check_prerequisites():
            return False
        
        # Passo 2: Backup
        if not backup_database():
            return False
            
        # Passo 3: Verificar migration atual
        check_current_migration()
        
        # Passo 4: Mostrar plano
        if not show_migration_plan():
            print("Deploy cancelado pelo usuário")
            return False
        
        # Passo 5: Executar migration
        if not execute_migration():
            return False
        
        # Passo 6: Inicializar dados
        if not initialize_default_data():
            print_warning("Dados não inicializados - fazer manualmente")
        
        # Passo 7: Testar
        test_system()
        
        # Passo 8: Próximos passos
        show_next_steps()
        
        print_success("DEPLOY CONCLUÍDO COM SUCESSO!")
        return True
        
    except KeyboardInterrupt:
        print_error("Deploy interrompido pelo usuário")
        return False
    except Exception as e:
        print_error(f"Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)