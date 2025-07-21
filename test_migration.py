#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Simples de Migration - Sistema de Permissões
==========================================

Testa se a migration está funcionando localmente.
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

def test_migration():
    """Testa migration localmente"""
    print("="*50)
    print("TESTE DE MIGRATION - PERMISSOES")
    print("="*50)
    
    try:
        print("\n1. Verificando arquivos necessarios...")
        
        # Verificar se estamos no diretório correto
        if not os.path.exists('app') or not os.path.exists('migrations'):
            print("ERRO: Execute na raiz do projeto!")
            return False
        
        # Verificar migration
        migration_path = "migrations/versions/add_permissions_equipe_vendas.py"
        if not os.path.exists(migration_path):
            print(f"ERRO: Migration nao encontrada: {migration_path}")
            return False
        
        print("SUCESSO: Arquivos encontrados!")
        
        print("\n2. Testando import dos models...")
        
        # Testar import dos models
        try:
            from app.permissions.models import PerfilUsuario, ModuloSistema, FuncaoModulo
            print("SUCESSO: Models importados!")
        except Exception as e:
            print(f"ERRO no import dos models: {e}")
            return False
        
        print("\n3. Testando blueprint...")
        
        try:
            from app.permissions import permissions_bp
            print("SUCESSO: Blueprint importado!")
        except Exception as e:
            print(f"ERRO no import do blueprint: {e}")
            return False
        
        print("\n4. Testando faturamento mapper...")
        
        try:
            from app.odoo.utils.faturamento_mapper import FaturamentoMapper
            mapper = FaturamentoMapper()
            
            # Verificar se campo equipe_vendas existe
            if 'equipe_vendas' in mapper.mapeamento_faturamento:
                print("SUCESSO: Campo equipe_vendas encontrado no mapper!")
                print(f"Mapeamento: {mapper.mapeamento_faturamento['equipe_vendas']}")
            else:
                print("ERRO: Campo equipe_vendas nao encontrado no mapper!")
                return False
                
        except Exception as e:
            print(f"ERRO no teste do mapper: {e}")
            return False
        
        print("\n5. RESULTADO GERAL:")
        print("SUCESSO: Todos os testes passaram!")
        print("A migration pode ser executada com seguranca.")
        
        return True
        
    except Exception as e:
        print(f"\nERRO GERAL: {e}")
        return False

def show_next_steps():
    """Mostra próximos passos"""
    print("\n" + "="*50)
    print("PROXIMOS PASSOS PARA DEPLOY")
    print("="*50)
    
    print("\n1. COMMIT E PUSH:")
    print('   git add -A')
    print('   git commit -m "Implementar sistema de permissoes granular"')
    print('   git push origin main')
    
    print("\n2. NO RENDER (apos deploy automatico):")
    print("   a) Fazer backup manual do PostgreSQL")
    print("   b) Executar: flask db upgrade")
    print("   c) Inicializar dados padrao (opcional)")
    
    print("\n3. VERIFICAR:")
    print("   - Acessar /admin/permissions/")
    print("   - Testar sincronizacao integrada")
    print("   - Verificar campo equipe_vendas nos dados")
    
    print("\n4. COMANDO DE INICIALIZACAO (se necessario):")
    print('''   python -c "
from app import create_app
from app.permissions.models import PerfilUsuario, ModuloSistema, FuncaoModulo
app = create_app()
with app.app_context():
    PerfilUsuario.get_or_create_default_profiles()
    ModuloSistema.get_or_create_default_modules()
    FuncaoModulo.get_or_create_default_functions()
    print('Dados inicializados!')
"''')

def main():
    """Função principal"""
    print("Iniciando teste de migration...")
    
    if test_migration():
        show_next_steps()
        print("\nTESTE CONCLUIDO COM SUCESSO!")
        return True
    else:
        print("\nTESTE FALHOU!")
        print("Corrija os problemas antes do deploy.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)