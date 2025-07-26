#!/usr/bin/env python3
"""
Teste do sistema Claude AI Novo em modo standalone (sem Flask)
"""

import os
import sys
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configurar ambiente para teste
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

def test_imports():
    """Testa se os imports funcionam corretamente"""
    print("\n🔍 Testando imports com fallback...")
    
    try:
        # Testar imports principais
        from app.claude_ai_novo.processors.response_processor import ResponseProcessor
        print("✅ ResponseProcessor importado")
        
        from app.claude_ai_novo.providers.data_provider import DataProvider
        print("✅ DataProvider importado")
        
        from app.claude_ai_novo.security.security_guard import SecurityGuard
        print("✅ SecurityGuard importado")
        
        from app.claude_ai_novo.orchestrators.main_orchestrator import MainOrchestrator
        print("✅ MainOrchestrator importado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos imports: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Testa funcionalidade básica em modo standalone"""
    print("\n🔍 Testando funcionalidade básica...")
    
    try:
        from app.claude_ai_novo.processors.response_processor import ResponseProcessor
        
        # Criar processador
        processor = ResponseProcessor()
        print("✅ ResponseProcessor criado")
        
        # Testar processamento simples
        resultado = processor._processar_consulta_padrao("teste de sistema", None)
        if resultado and len(resultado) > 0:
            print("✅ Processamento básico funcionando")
            print(f"   Resposta tem {len(resultado)} caracteres")
            return True
        else:
            print("❌ Processamento retornou vazio")
            return False
            
    except Exception as e:
        print(f"❌ Erro na funcionalidade: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_security():
    """Testa módulo de segurança"""
    print("\n🔍 Testando módulo de segurança...")
    
    try:
        from app.claude_ai_novo.security.security_guard import SecurityGuard
        
        # Criar guarda
        guard = SecurityGuard()
        print("✅ SecurityGuard criado")
        
        # Testar validação básica
        is_valid = guard.validate_input("consulta normal de teste")
        if is_valid:
            print("✅ Validação de input funcionando")
        
        # Testar detecção de SQL injection
        is_invalid = guard.validate_query("'; DROP TABLE users; --")
        if not is_invalid:
            print("✅ Detecção de SQL injection funcionando")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de segurança: {e}")
        return False

def test_data_provider():
    """Testa o DataProvider"""
    print("\n🔍 Testando DataProvider...")
    
    try:
        from app.claude_ai_novo.providers.data_provider import DataProvider
        
        # Criar provider
        provider = DataProvider()
        print("✅ DataProvider criado")
        
        # Testar método básico
        result = provider.get_data_by_domain("teste", {})
        if isinstance(result, dict):
            print("✅ DataProvider retornando dados")
            return True
        else:
            print("❌ DataProvider não retornou dict")
            return False
            
    except Exception as e:
        print(f"❌ Erro no DataProvider: {e}")
        return False

def main():
    """Função principal"""
    print("="*60)
    print("🚀 TESTE STANDALONE - CLAUDE AI NOVO")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Executar testes
    results = {
        'imports': test_imports(),
        'functionality': test_basic_functionality(),
        'security': test_security(),
        'data_provider': test_data_provider(),
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
        print("\n🎉 SISTEMA FUNCIONANDO EM MODO STANDALONE! 🎉")
        print("\nPróximos passos:")
        print("1. Configure as variáveis de ambiente no Render")
        print("2. Adicione as dependências ao requirements.txt")
        print("3. Faça o deploy seguindo o checklist")
        return 0
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os problemas.")
        return 1

if __name__ == "__main__":
    sys.exit(main())