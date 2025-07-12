#!/usr/bin/env python3
"""
🔍 TESTE SECURITY GUARD
======================

Script para testar o SecurityGuard e verificar se está funcionando corretamente.
"""

import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adicionar caminho para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_security_guard():
    """Teste do SecurityGuard"""
    
    print("🔍 TESTANDO SECURITY GUARD")
    print("=" * 50)
    
    try:
        # Importar SecurityGuard
        from app.claude_ai_novo.security.security_guard import SecurityGuard
        
        # Criar instância
        guard = SecurityGuard()
        
        # Verificar configurações
        print(f"🔐 Modo produção: {guard.is_production}")
        print(f"🆕 Sistema novo ativo: {guard.new_system_active}")
        
        # Variáveis de ambiente relevantes
        print(f"🌍 FLASK_ENV: {os.getenv('FLASK_ENV', 'N/A')}")
        print(f"🌍 ENVIRONMENT: {os.getenv('ENVIRONMENT', 'N/A')}")
        print(f"🌍 RENDER: {os.getenv('RENDER', 'N/A')}")
        print(f"🌍 PORT: {os.getenv('PORT', 'N/A')}")
        print(f"🌍 RENDER_EXTERNAL_URL: {os.getenv('RENDER_EXTERNAL_URL', 'N/A')}")
        print(f"🌍 USE_NEW_CLAUDE_SYSTEM: {os.getenv('USE_NEW_CLAUDE_SYSTEM', 'N/A')}")
        
        print("\n🧪 TESTANDO OPERAÇÕES")
        print("-" * 30)
        
        # Testar operações diferentes
        operations = [
            'intelligent_query',
            'process_query',
            'analyze_query',
            'admin',
            'delete_all',
            'system_reset'
        ]
        
        for operation in operations:
            result = guard.validate_user_access(operation)
            status = "✅ PERMITIDO" if result else "❌ NEGADO"
            print(f"{status}: {operation}")
        
        print("\n🔍 INFORMAÇÕES DE SEGURANÇA")
        print("-" * 30)
        
        security_info = guard.get_security_info()
        for key, value in security_info.items():
            print(f"{key}: {value}")
        
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_production_env():
    """Simula ambiente de produção"""
    print("\n🌍 SIMULANDO AMBIENTE DE PRODUÇÃO")
    print("=" * 50)
    
    # Definir variáveis de ambiente de produção
    os.environ['FLASK_ENV'] = 'production'
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['RENDER'] = 'true'
    os.environ['PORT'] = '10000'
    os.environ['RENDER_EXTERNAL_URL'] = 'https://sistema-fretes.onrender.com'
    os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'
    
    # Testar novamente
    return test_security_guard()

if __name__ == "__main__":
    print("🧪 TESTE SECURITY GUARD - INÍCIO")
    print("=" * 60)
    
    # Teste inicial
    success1 = test_security_guard()
    
    # Teste com simulação de produção
    success2 = simulate_production_env()
    
    print("\n📊 RESUMO DOS TESTES")
    print("=" * 60)
    print(f"Teste inicial: {'✅ SUCESSO' if success1 else '❌ FALHA'}")
    print(f"Teste produção: {'✅ SUCESSO' if success2 else '❌ FALHA'}")
    
    if success1 and success2:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM!") 