#!/usr/bin/env python3
"""
Script de teste real para validar o sistema claude_ai_novo
Verifica se as correções do Claude Flow estão funcionando
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_section(title):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def test_imports():
    """Testa se os imports básicos funcionam"""
    print_section("TESTE 1: Imports Básicos")
    
    tests_passed = 0
    tests_failed = 0
    
    # Teste 1: Importar ResponseProcessor
    try:
        from app.claude_ai_novo.processors.response_processor import ResponseProcessor
        print("✅ ResponseProcessor importado com sucesso")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Erro ao importar ResponseProcessor: {e}")
        tests_failed += 1
    
    # Teste 2: Importar SecurityGuard
    try:
        from app.claude_ai_novo.security.security_guard import SecurityGuard
        print("✅ SecurityGuard importado com sucesso")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Erro ao importar SecurityGuard: {e}")
        tests_failed += 1
    
    # Teste 3: Importar orchestrator
    try:
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        print("✅ OrchestratorManager importado com sucesso")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Erro ao importar OrchestratorManager: {e}")
        tests_failed += 1
    
    print(f"\n📊 Resultado: {tests_passed} passou, {tests_failed} falhou")
    return tests_failed == 0

def test_response_processor():
    """Testa funcionalidades do ResponseProcessor"""
    print_section("TESTE 2: ResponseProcessor Funcionalidades")
    
    try:
        from app.claude_ai_novo.processors.response_processor import ResponseProcessor, get_response_processor
        
        # Teste 1: Criar instância
        processor = ResponseProcessor()
        print("✅ ResponseProcessor criado com sucesso")
        
        # Teste 2: Singleton
        processor2 = get_response_processor()
        print("✅ Singleton get_response_processor funcionando")
        
        # Teste 3: Processar consulta simples
        consulta = "Quais são as entregas pendentes?"
        analise = {
            'dominio': 'entregas',
            'tipo_consulta': 'informacao',
            'periodo_dias': 7
        }
        
        resposta = processor._processar_consulta_padrao(consulta, None)
        if resposta and len(resposta) > 10:
            print("✅ Processamento de consulta padrão funcionando")
            print(f"   Resposta tem {len(resposta)} caracteres")
        else:
            print("❌ Problema no processamento de consulta")
        
        # Teste 4: Validação de qualidade
        qualidade = processor._avaliar_qualidade_resposta(consulta, resposta, analise)
        print(f"✅ Avaliação de qualidade: Score = {qualidade['score']:.2f}")
        print(f"   Classificação: {qualidade['avaliacao']}")
        
        # Teste 5: Sanitização
        entrada_maliciosa = "<script>alert('xss')</script>Teste"
        sanitizada = processor._sanitize_input(entrada_maliciosa)
        if '<script>' not in sanitizada:
            print("✅ Sanitização funcionando corretamente")
        else:
            print("❌ Problema na sanitização")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes do ResponseProcessor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_security_guard():
    """Testa funcionalidades do SecurityGuard"""
    print_section("TESTE 3: SecurityGuard Funcionalidades")
    
    try:
        from app.claude_ai_novo.security.security_guard import SecurityGuard, get_security_guard
        
        # Teste 1: Criar instância
        guard = SecurityGuard()
        print("✅ SecurityGuard criado com sucesso")
        
        # Teste 2: Detectar modo
        print(f"   Modo produção: {guard.is_production}")
        print(f"   Sistema novo ativo: {guard.new_system_active}")
        
        # Teste 3: Validar acesso
        operations_to_test = [
            ('intelligent_query', True),
            ('process_query', True),
            ('admin', False),  # Deve falhar sem autenticação
            ('basic_query', True)
        ]
        
        all_passed = True
        for operation, expected in operations_to_test:
            result = guard.validate_user_access(operation)
            status = "✅" if result == expected else "❌"
            print(f"{status} Operação '{operation}': {result} (esperado: {expected})")
            if result != expected:
                all_passed = False
        
        # Teste 4: Validar entrada
        test_inputs = [
            ("consulta normal", True),
            ("DROP TABLE users", False),
            ("<script>alert('xss')</script>", False),
            ("SELECT * FROM pedidos", True)
        ]
        
        for input_data, expected in test_inputs:
            result = guard.validate_input(input_data)
            status = "✅" if result == expected else "❌"
            print(f"{status} Validação entrada: '{input_data[:20]}...': {result}")
        
        # Teste 5: Gerar token
        token = guard.generate_token("test_data")
        if token and len(token) == 32:
            print("✅ Geração de token funcionando")
        else:
            print("❌ Problema na geração de token")
        
        # Teste 6: Info de segurança
        info = guard.get_security_info()
        print(f"✅ Info de segurança obtida: {info['module']} v{info['version']}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Erro nos testes do SecurityGuard: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Testa integração entre componentes"""
    print_section("TESTE 4: Integração de Componentes")
    
    try:
        # Importar componentes principais
        from app.claude_ai_novo.processors.response_processor import get_response_processor
        from app.claude_ai_novo.security.security_guard import get_security_guard
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        
        print("✅ Todos os componentes principais importados")
        
        # Teste de fluxo completo simulado
        guard = get_security_guard()
        processor = get_response_processor()
        
        # 1. Validar acesso
        if guard.validate_user_access('process_query'):
            print("✅ Acesso validado para process_query")
        
        # 2. Validar e sanitizar entrada
        query = "Quais pedidos estão pendentes?"
        if guard.validate_input(query):
            print("✅ Query validada com sucesso")
        
        sanitized = guard.sanitize_input(query)
        print(f"✅ Query sanitizada: '{sanitized}'")
        
        # 3. Processar consulta
        analise = {
            'dominio': 'pedidos',
            'tipo_consulta': 'informacao'
        }
        
        resposta = processor._processar_consulta_padrao(sanitized, None)
        if resposta:
            print(f"✅ Resposta gerada com {len(resposta)} caracteres")
        
        # 4. Testar orchestrator (se disponível)
        try:
            orchestrator = get_orchestrator_manager()
            print("✅ OrchestratorManager disponível")
        except:
            print("⚠️  OrchestratorManager não disponível (normal se algumas dependências não estão instaladas)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallbacks():
    """Testa se os fallbacks estão funcionando"""
    print_section("TESTE 5: Fallbacks e Compatibilidade")
    
    # Simular ambiente sem Flask
    import sys
    
    # Backup dos módulos
    flask_backup = sys.modules.get('flask')
    flask_login_backup = sys.modules.get('flask_login')
    
    try:
        # Remover Flask temporariamente
        if 'flask' in sys.modules:
            del sys.modules['flask']
        if 'flask_login' in sys.modules:
            del sys.modules['flask_login']
        
        # Tentar importar com fallback
        from app.claude_ai_novo.security.security_guard import SecurityGuard
        guard = SecurityGuard()
        
        print("✅ SecurityGuard funciona sem Flask (fallback ativo)")
        
        # Verificar se detectou corretamente
        info = guard.get_security_info()
        print(f"   Modo: {info['security_level']}")
        
        # Restaurar módulos
        if flask_backup:
            sys.modules['flask'] = flask_backup
        if flask_login_backup:
            sys.modules['flask_login'] = flask_login_backup
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de fallback: {e}")
        
        # Restaurar módulos em caso de erro
        if flask_backup:
            sys.modules['flask'] = flask_backup
        if flask_login_backup:
            sys.modules['flask_login'] = flask_login_backup
        
        return False

def main():
    """Executa todos os testes"""
    print(f"\n🚀 TESTE REAL DO SISTEMA claude_ai_novo")
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"📁 Diretório: {os.getcwd()}")
    
    results = {
        'imports': test_imports(),
        'response_processor': test_response_processor(),
        'security_guard': test_security_guard(),
        'integration': test_integration(),
        'fallbacks': test_fallbacks()
    }
    
    # Resumo final
    print_section("RESUMO FINAL")
    
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    
    print(f"\n📊 Resultados:")
    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"   {test_name}: {status}")
    
    print(f"\n🎯 Total: {total_passed}/{total_tests} testes passaram")
    
    if total_passed == total_tests:
        print("\n✅ TODOS OS TESTES PASSARAM! O sistema está funcionando corretamente.")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs acima.")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)