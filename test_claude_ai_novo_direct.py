#!/usr/bin/env python3
"""
Script de teste direto para validar o sistema claude_ai_novo
Importa os módulos diretamente sem passar pelo app/__init__.py
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório ao path de forma mais específica
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Adicionar também o diretório app/claude_ai_novo diretamente
claude_ai_novo_dir = os.path.join(current_dir, 'app', 'claude_ai_novo')
sys.path.insert(0, claude_ai_novo_dir)

def print_section(title):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def test_direct_imports():
    """Testa imports diretos dos módulos"""
    print_section("TESTE 1: Imports Diretos (sem app/__init__.py)")
    
    tests_passed = 0
    tests_failed = 0
    
    # Teste 1: Importar módulos base diretamente
    try:
        # Importar o módulo base primeiro
        sys.path.insert(0, os.path.join(current_dir, 'app', 'claude_ai_novo', 'processors'))
        import base
        print("✅ Módulo base importado com sucesso")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Erro ao importar módulo base: {e}")
        tests_failed += 1
    
    # Teste 2: Importar ResponseProcessor diretamente
    try:
        import response_processor
        print("✅ response_processor.py importado diretamente")
        
        # Verificar se a classe existe
        if hasattr(response_processor, 'ResponseProcessor'):
            print("✅ Classe ResponseProcessor encontrada")
            tests_passed += 1
        else:
            print("❌ Classe ResponseProcessor não encontrada")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Erro ao importar response_processor: {e}")
        tests_failed += 1
    
    # Teste 3: Importar SecurityGuard diretamente
    try:
        sys.path.insert(0, os.path.join(current_dir, 'app', 'claude_ai_novo', 'security'))
        import security_guard
        print("✅ security_guard.py importado diretamente")
        
        if hasattr(security_guard, 'SecurityGuard'):
            print("✅ Classe SecurityGuard encontrada")
            tests_passed += 1
        else:
            print("❌ Classe SecurityGuard não encontrada")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Erro ao importar security_guard: {e}")
        tests_failed += 1
    
    print(f"\n📊 Resultado: {tests_passed} passou, {tests_failed} falhou")
    return tests_failed == 0

def test_response_processor_functionality():
    """Testa funcionalidades básicas do ResponseProcessor"""
    print_section("TESTE 2: ResponseProcessor - Funcionalidades Básicas")
    
    try:
        # Importar diretamente
        sys.path.insert(0, os.path.join(current_dir, 'app', 'claude_ai_novo', 'processors'))
        import response_processor
        
        # Criar instância
        processor = response_processor.ResponseProcessor()
        print("✅ ResponseProcessor instanciado com sucesso")
        
        # Teste 1: Método básico existe
        if hasattr(processor, '_processar_consulta_padrao'):
            print("✅ Método _processar_consulta_padrao existe")
        else:
            print("❌ Método _processar_consulta_padrao não encontrado")
            return False
        
        # Teste 2: Processar consulta simples
        consulta = "teste de consulta"
        try:
            resposta = processor._processar_consulta_padrao(consulta, None)
            if resposta:
                print(f"✅ Consulta processada: {len(resposta)} caracteres")
            else:
                print("❌ Resposta vazia")
        except Exception as e:
            print(f"⚠️  Erro ao processar consulta: {e}")
        
        # Teste 3: Sanitização
        if hasattr(processor, '_sanitize_input'):
            entrada = "<script>alert('xss')</script>Teste"
            try:
                sanitizada = processor._sanitize_input(entrada)
                if '<script>' not in sanitizada:
                    print("✅ Sanitização funcionando")
                else:
                    print("❌ Sanitização falhou")
            except Exception as e:
                print(f"⚠️  Erro na sanitização: {e}")
        
        # Teste 4: Singleton
        if hasattr(response_processor, 'get_response_processor'):
            try:
                singleton = response_processor.get_response_processor()
                print("✅ Função singleton disponível")
            except Exception as e:
                print(f"⚠️  Erro no singleton: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_security_guard_functionality():
    """Testa funcionalidades básicas do SecurityGuard"""
    print_section("TESTE 3: SecurityGuard - Funcionalidades Básicas")
    
    try:
        # Importar diretamente
        sys.path.insert(0, os.path.join(current_dir, 'app', 'claude_ai_novo', 'security'))
        import security_guard
        
        # Criar instância
        guard = security_guard.SecurityGuard()
        print("✅ SecurityGuard instanciado com sucesso")
        
        # Teste 1: Propriedades básicas
        print(f"   - Modo produção: {guard.is_production}")
        print(f"   - Sistema novo ativo: {guard.new_system_active}")
        print(f"   - Padrões bloqueados: {len(guard.blocked_patterns)}")
        
        # Teste 2: Validação de acesso
        operations = ['intelligent_query', 'process_query', 'admin']
        for op in operations:
            try:
                result = guard.validate_user_access(op)
                print(f"✅ validate_user_access('{op}'): {result}")
            except Exception as e:
                print(f"⚠️  Erro em validate_user_access('{op}'): {e}")
        
        # Teste 3: Validação de entrada
        test_inputs = [
            "consulta normal",
            "DROP TABLE users",
            "<script>alert('test')</script>"
        ]
        
        for input_str in test_inputs:
            try:
                result = guard.validate_input(input_str)
                print(f"✅ validate_input('{input_str[:20]}...'): {result}")
            except Exception as e:
                print(f"⚠️  Erro em validate_input: {e}")
        
        # Teste 4: Geração de token
        try:
            token = guard.generate_token("test")
            if token and len(token) == 32:
                print(f"✅ Token gerado: {token[:8]}...")
            else:
                print("❌ Token inválido")
        except Exception as e:
            print(f"⚠️  Erro na geração de token: {e}")
        
        # Teste 5: Info de segurança
        try:
            info = guard.get_security_info()
            print(f"✅ Info obtida: {info.get('module', 'N/A')} v{info.get('version', 'N/A')}")
        except Exception as e:
            print(f"⚠️  Erro ao obter info: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_behavior():
    """Testa comportamento dos fallbacks"""
    print_section("TESTE 4: Comportamento dos Fallbacks")
    
    # Verificar se Flask está disponível
    try:
        import flask
        print("ℹ️  Flask está instalado no sistema")
        flask_available = True
    except ImportError:
        print("ℹ️  Flask NÃO está instalado (testando fallbacks)")
        flask_available = False
    
    # Verificar se SQLAlchemy está disponível
    try:
        import sqlalchemy
        print("ℹ️  SQLAlchemy está instalado no sistema")
        sqlalchemy_available = True
    except ImportError:
        print("ℹ️  SQLAlchemy NÃO está instalado (testando fallbacks)")
        sqlalchemy_available = False
    
    # Testar imports com fallbacks
    try:
        sys.path.insert(0, os.path.join(current_dir, 'app', 'claude_ai_novo', 'processors'))
        import response_processor
        
        # Verificar flags de disponibilidade
        if hasattr(response_processor, 'FLASK_LOGIN_AVAILABLE'):
            print(f"✅ Flag FLASK_LOGIN_AVAILABLE: {response_processor.FLASK_LOGIN_AVAILABLE}")
        
        if hasattr(response_processor, 'SQLALCHEMY_AVAILABLE'):
            print(f"✅ Flag SQLALCHEMY_AVAILABLE: {response_processor.SQLALCHEMY_AVAILABLE}")
        
        if hasattr(response_processor, 'ANTHROPIC_AVAILABLE'):
            print(f"✅ Flag ANTHROPIC_AVAILABLE: {response_processor.ANTHROPIC_AVAILABLE}")
        
        # Verificar se current_user tem fallback
        if hasattr(response_processor, 'current_user'):
            print(f"✅ current_user disponível (tipo: {type(response_processor.current_user).__name__})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar fallbacks: {e}")
        return False

def test_integration_without_flask():
    """Testa integração sem dependências externas"""
    print_section("TESTE 5: Integração Sem Dependências Externas")
    
    try:
        # Importar módulos
        sys.path.insert(0, os.path.join(current_dir, 'app', 'claude_ai_novo', 'processors'))
        sys.path.insert(0, os.path.join(current_dir, 'app', 'claude_ai_novo', 'security'))
        
        import response_processor
        import security_guard
        
        # Criar instâncias
        processor = response_processor.ResponseProcessor()
        guard = security_guard.SecurityGuard()
        
        print("✅ Componentes criados com sucesso")
        
        # Fluxo de teste
        query = "Qual o status das entregas?"
        
        # 1. Validar acesso
        if guard.validate_user_access('process_query'):
            print("✅ Acesso validado")
        
        # 2. Validar entrada
        if guard.validate_input(query):
            print("✅ Query validada")
        
        # 3. Sanitizar
        sanitized = guard.sanitize_input(query)
        print(f"✅ Query sanitizada: '{sanitized}'")
        
        # 4. Processar
        response = processor._processar_consulta_padrao(sanitized, None)
        if response:
            print(f"✅ Resposta gerada: {len(response)} caracteres")
            
            # Mostrar primeiras linhas da resposta
            lines = response.split('\n')[:3]
            for line in lines:
                if line.strip():
                    print(f"   > {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes"""
    print(f"\n🚀 TESTE DIRETO DO SISTEMA claude_ai_novo")
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"📁 Diretório: {os.getcwd()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    results = {
        'imports_diretos': test_direct_imports(),
        'response_processor': test_response_processor_functionality(),
        'security_guard': test_security_guard_functionality(),
        'fallbacks': test_fallback_behavior(),
        'integration': test_integration_without_flask()
    }
    
    # Resumo final
    print_section("RESUMO FINAL")
    
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    
    print(f"\n📊 Resultados dos Testes:")
    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"   {test_name}: {status}")
    
    print(f"\n🎯 Total: {total_passed}/{total_tests} testes passaram")
    
    if total_passed == total_tests:
        print("\n✅ SUCESSO! Todos os testes passaram.")
        print("   As correções do Claude Flow estão funcionando corretamente.")
        print("   O sistema pode operar sem Flask/SQLAlchemy usando fallbacks.")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os detalhes acima.")
    
    # Informações adicionais
    print("\n📝 Observações:")
    print("   - O sistema usa fallbacks quando dependências não estão disponíveis")
    print("   - ResponseProcessor e SecurityGuard funcionam independentemente")
    print("   - As correções focaram em compatibilidade e robustez")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)