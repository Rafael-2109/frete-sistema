#!/usr/bin/env python3
"""
🔍 TESTE FLASK DETALHADO - Identificar erro UTF-8 específico
===========================================================

Script para identificar onde exatamente o erro UTF-8 está ocorrendo.
"""

import os
import sys
import traceback
from pathlib import Path

# Configurar path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_step_by_step():
    """Testa passo a passo a inicialização do Flask"""
    
    print("🔍 TESTE FLASK DETALHADO - PASSO A PASSO")
    print("=" * 60)
    
    # Passo 1: Tentar import básico
    print("\n📋 PASSO 1: Import básico")
    try:
        print("   Tentando: from app import create_app")
        from app import create_app
        print("   ✅ Import OK")
    except Exception as e:
        print(f"   ❌ Import falhou: {e}")
        print("   🔍 Traceback:")
        traceback.print_exc()
        return False
    
    # Passo 2: Tentar create_app sem argumentos
    print("\n📋 PASSO 2: create_app() sem argumentos")
    try:
        print("   Tentando: create_app()")
        app = create_app()
        print("   ✅ create_app() OK")
        print(f"   📊 App criado: {type(app)}")
        return True
    except UnicodeDecodeError as e:
        print(f"   ❌ ERRO UTF-8: {e}")
        print(f"   📍 Posição: {e.start}-{e.end}")
        print(f"   🔤 Encoding: {e.encoding}")
        print(f"   📄 Objeto: {e.object}")
        print("   🔍 Traceback:")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"   ❌ Outro erro: {e}")
        print("   🔍 Traceback:")
        traceback.print_exc()
        return False

def test_config_loading():
    """Testa carregamento de configurações"""
    
    print("\n🔧 TESTE DE CONFIGURAÇÕES")
    print("=" * 60)
    
    # Testar imports de configuração
    try:
        print("   Tentando: import config")
        import config
        print("   ✅ Config importado")
        
        # Verificar configurações
        print(f"   📊 Config class: {config.Config}")
        
        # Verificar DATABASE_URL
        db_url = getattr(config.Config, 'DATABASE_URL', None)
        if db_url:
            print(f"   💾 DATABASE_URL: {len(db_url)} caracteres")
            
            # Verificar se há caracteres problemáticos
            for i, char in enumerate(db_url):
                if ord(char) > 127:
                    print(f"   ⚠️ Caractere não-ASCII na posição {i}: '{char}' (código: {ord(char)})")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro ao carregar config: {e}")
        traceback.print_exc()
        return False

def test_database_connection():
    """Testa conexão com banco de dados"""
    
    print("\n🗄️ TESTE DE CONEXÃO COM BANCO")
    print("=" * 60)
    
    try:
        print("   Tentando: importar SQLAlchemy")
        from flask_sqlalchemy import SQLAlchemy
        print("   ✅ SQLAlchemy importado")
        
        # Verificar DATABASE_URL
        db_url = os.getenv('DATABASE_URL', '')
        if db_url:
            print(f"   💾 DATABASE_URL: {len(db_url)} caracteres")
            
            # Verificar se tem caracteres problemáticos
            problematic_chars = []
            for i, char in enumerate(db_url):
                if ord(char) > 127:
                    problematic_chars.append((i, char, ord(char)))
            
            if problematic_chars:
                print(f"   ⚠️ Encontrados {len(problematic_chars)} caracteres problemáticos:")
                for pos, char, code in problematic_chars:
                    print(f"      Posição {pos}: '{char}' (código: {code})")
                return False
            else:
                print("   ✅ DATABASE_URL - todos os caracteres são ASCII")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro no teste de banco: {e}")
        traceback.print_exc()
        return False

def test_app_context():
    """Testa contexto da aplicação"""
    
    print("\n🏗️ TESTE DE CONTEXTO DA APLICAÇÃO")
    print("=" * 60)
    
    try:
        print("   Tentando: criar contexto de aplicação")
        from app import create_app
        
        # Criar app com configuração mínima
        app = create_app()
        
        with app.app_context():
            print("   ✅ Contexto da aplicação criado")
            print(f"   📊 App name: {app.name}")
            print(f"   🔧 Config: {app.config}")
            
            # Testar acesso ao banco
            try:
                from app import db
                print(f"   💾 Database: {db}")
                print("   ✅ Database acessível")
            except Exception as e:
                print(f"   ⚠️ Database não acessível: {e}")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro no contexto: {e}")
        traceback.print_exc()
        return False

def test_full_initialization():
    """Testa inicialização completa"""
    
    print("\n🚀 TESTE DE INICIALIZAÇÃO COMPLETA")
    print("=" * 60)
    
    try:
        print("   Tentando: inicialização completa")
        from app import create_app
        
        # Criar app
        app = create_app()
        
        # Testar blueprints
        print(f"   📱 Blueprints: {list(app.blueprints.keys())}")
        
        # Testar extensões
        print(f"   🔌 Extensions: {list(app.extensions.keys())}")
        
        print("   ✅ Inicialização completa OK")
        return True
    except Exception as e:
        print(f"   ❌ Erro na inicialização: {e}")
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    
    print("🔍 TESTE FLASK DETALHADO - INÍCIO")
    print("=" * 70)
    
    # Executar testes
    tests = [
        ("Passo a passo", test_step_by_step),
        ("Configurações", test_config_loading),
        ("Banco de dados", test_database_connection),
        ("Contexto da aplicação", test_app_context),
        ("Inicialização completa", test_full_initialization)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ PASSOU" if result else "❌ FALHOU"
            print(f"\n🎯 {test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            print(f"\n💥 {test_name}: ERRO - {e}")
    
    # Resumo
    print("\n📊 RESUMO DOS TESTES")
    print("=" * 70)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n🎯 RESULTADO FINAL: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM - verifique os logs acima")

if __name__ == "__main__":
    main() 