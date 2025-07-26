#!/usr/bin/env python3
"""
Script de teste de integração para verificar se o sistema está pronto para o Render
"""

import os
import sys
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_environment():
    """Testa variáveis de ambiente"""
    print("\n🔍 Testando Variáveis de Ambiente...")
    
    required_vars = {
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'USE_NEW_CLAUDE_SYSTEM': os.getenv('USE_NEW_CLAUDE_SYSTEM'),
    }
    
    all_ok = True
    for var, value in required_vars.items():
        if value:
            print(f"✅ {var}: Configurada")
        else:
            print(f"❌ {var}: NÃO configurada")
            all_ok = False
    
    return all_ok

def test_imports():
    """Testa imports principais"""
    print("\n🔍 Testando Imports...")
    
    imports_to_test = [
        ('app.claude_ai_novo', 'ClaudeAINovo'),
        ('app.claude_ai_novo.api', 'health_blueprint'),
        ('app.claude_ai_novo.orchestrators', 'MainOrchestrator'),
        ('app.claude_ai_novo.providers', 'DataProvider'),
    ]
    
    all_ok = True
    for module_name, class_name in imports_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}: OK")
        except Exception as e:
            print(f"❌ {module_name}.{class_name}: {str(e)}")
            all_ok = False
    
    return all_ok

def test_basic_functionality():
    """Testa funcionalidade básica"""
    print("\n🔍 Testando Funcionalidade Básica...")
    
    try:
        from app.claude_ai_novo import ClaudeAINovo
        
        # Criar instância
        claude_ai = ClaudeAINovo()
        print("✅ Instância criada com sucesso")
        
        # Testar consulta simples
        resultado = claude_ai.processar_consulta("teste")
        if resultado:
            print("✅ Processamento de consulta: OK")
            return True
        else:
            print("❌ Processamento de consulta: Falhou")
            return False
            
    except Exception as e:
        print(f"❌ Erro na funcionalidade básica: {str(e)}")
        return False

def test_health_endpoints():
    """Testa endpoints de health check"""
    print("\n🔍 Testando Health Check Endpoints...")
    
    try:
        from app.claude_ai_novo.api.health_check import (
            health_check, liveness_probe, readiness_probe
        )
        
        # Simular contexto Flask
        from flask import Flask
        app = Flask(__name__)
        
        with app.test_request_context():
            # Testar health check principal
            response, status = health_check()
            print(f"✅ Health Check: Status {status}")
            
            # Testar liveness
            response, status = liveness_probe()
            print(f"✅ Liveness Probe: Status {status}")
            
            # Testar readiness
            response, status = readiness_probe()
            print(f"✅ Readiness Probe: Status {status}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro nos health endpoints: {str(e)}")
        return False

def main():
    """Função principal"""
    print("="*60)
    print("🚀 TESTE DE INTEGRAÇÃO - CLAUDE AI NOVO")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Executar testes
    results = {
        'environment': test_environment(),
        'imports': test_imports(),
        'functionality': test_basic_functionality(),
        'health': test_health_endpoints(),
    }
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name.upper()}: {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} testes passaram")
    
    if passed_tests == total_tests:
        print("\n🎉 SISTEMA PRONTO PARA DEPLOY NO RENDER! 🎉")
        return 0
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os problemas antes do deploy.")
        return 1

if __name__ == "__main__":
    sys.exit(main())