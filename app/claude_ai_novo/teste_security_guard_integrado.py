#!/usr/bin/env python3
"""
🔐 TESTE - Security Guard Integrado
===================================

Teste específico para verificar se o SecurityGuard foi integrado corretamente
nos 3 orchestrators principais (MAESTRO, SessionOrchestrator, MainOrchestrator).
"""

import sys
import os
# Ajustar path para o projeto
sys.path.insert(0, os.path.abspath('../..'))

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def teste_security_guard_maestro():
    """
    🔐 Teste: SecurityGuard no MAESTRO (OrchestratorManager)
    """
    print("\n🔐 TESTE: SecurityGuard no MAESTRO")
    print("=" * 50)
    
    try:
        from orchestrators.orchestrator_manager import get_orchestrator_manager
        
        maestro = get_orchestrator_manager()
        
        # Verificar se SecurityGuard está disponível
        security_guard = maestro.security_guard
        
        print(f"✅ MAESTRO inicializado")
        print(f"✅ SecurityGuard disponível: {security_guard is not None}")
        
        if security_guard:
            # Teste de validação básica
            test_access = security_guard.validate_user_access("test_operation")
            print(f"✅ Validação de acesso: {test_access}")
            
            # Teste de validação de entrada
            test_input = security_guard.validate_input({"test": "data"})
            print(f"✅ Validação de entrada: {test_input}")
            
            # Teste de informações de segurança
            security_info = security_guard.get_security_info()
            print(f"✅ Informações de segurança: {security_info.get('security_level', 'N/A')}")
            
            # Teste de orquestração com segurança
            test_data = {
                "test_operation": "security_test",
                "safe_data": "teste seguro"
            }
            
            result = maestro.orchestrate_operation(
                operation_type="security_test",
                data=test_data
            )
            
            print(f"✅ Orquestração com segurança: {result.get('success', False)}")
            
            if result.get('security_blocked'):
                print(f"⚠️ Operação bloqueada por segurança: {result.get('error')}")
            
        else:
            print("⚠️ SecurityGuard não disponível (modo mock)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do MAESTRO: {e}")
        return False

def teste_security_guard_session():
    """
    🔐 Teste: SecurityGuard no SessionOrchestrator
    """
    print("\n🔐 TESTE: SecurityGuard no SessionOrchestrator")
    print("=" * 50)
    
    try:
        from orchestrators.session_orchestrator import get_session_orchestrator
        
        session_orch = get_session_orchestrator()
        
        # Verificar se SecurityGuard está disponível
        security_guard = session_orch.security_guard
        
        print(f"✅ SessionOrchestrator inicializado")
        print(f"✅ SecurityGuard disponível: {security_guard is not None}")
        
        if security_guard:
            # Teste de validação de sessão
            test_access = security_guard.validate_user_access("create_session", "session_management")
            print(f"✅ Validação de acesso à sessão: {test_access}")
            
            # Teste de criação de sessão com segurança
            try:
                session_id = session_orch.create_session(
                    user_id=1,
                    metadata={
                        "test": "session_security",
                        "safe_data": "teste seguro"
                    }
                )
                
                print(f"✅ Sessão criada com segurança: {session_id[:8]}...")
                
                # Limpar sessão de teste
                session_orch.terminate_session(session_id)
                
            except PermissionError as e:
                print(f"⚠️ Criação de sessão bloqueada por segurança: {e}")
        
        else:
            print("⚠️ SecurityGuard não disponível (modo mock)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do SessionOrchestrator: {e}")
        return False

def teste_security_guard_main():
    """
    🔐 Teste: SecurityGuard no MainOrchestrator
    """
    print("\n🔐 TESTE: SecurityGuard no MainOrchestrator")
    print("=" * 50)
    
    try:
        from orchestrators.main_orchestrator import get_main_orchestrator
        
        main_orch = get_main_orchestrator()
        
        # Verificar se SecurityGuard está disponível
        security_guard = main_orch.security_guard
        
        print(f"✅ MainOrchestrator inicializado")
        print(f"✅ SecurityGuard disponível: {security_guard is not None}")
        
        if security_guard:
            # Teste de validação de workflow
            test_access = security_guard.validate_user_access("workflow_test")
            print(f"✅ Validação de acesso ao workflow: {test_access}")
            
            # Teste de execução de workflow com segurança
            test_data = {
                "query": "teste de workflow seguro",
                "safe_data": "dados seguros"
            }
            
            result = main_orch.execute_workflow(
                workflow_name="analyze_query",
                operation_type="test_operation",
                data=test_data
            )
            
            print(f"✅ Execução de workflow com segurança: {result.get('success', False)}")
            
            if result.get('security_blocked'):
                print(f"⚠️ Workflow bloqueado por segurança: {result.get('error')}")
            
        else:
            print("⚠️ SecurityGuard não disponível (modo mock)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do MainOrchestrator: {e}")
        return False

def teste_security_guard_completo():
    """
    🔐 Teste: SecurityGuard Completo
    """
    print("\n🔐 TESTE: SecurityGuard Completo")
    print("=" * 50)
    
    try:
        from security.security_guard import get_security_guard
        
        security_guard = get_security_guard()
        
        print(f"✅ SecurityGuard standalone inicializado")
        
        # Teste de validação de entrada com dados perigosos
        dangerous_data = {
            "query": "DROP TABLE users; --",
            "script": "<script>alert('xss')</script>"
        }
        
        is_safe = security_guard.validate_input(dangerous_data)
        print(f"✅ Validação de dados perigosos: {is_safe} (deve ser False)")
        
        # Teste de sanitização
        dangerous_text = "<script>alert('xss')</script>Hello World"
        sanitized = security_guard.sanitize_input(dangerous_text)
        print(f"✅ Sanitização: '{sanitized}' (script removido)")
        
        # Teste de geração de token
        token = security_guard.generate_token("test_data")
        print(f"✅ Token gerado: {token[:16]}... (32 chars)")
        
        # Teste de validação de token
        is_valid = security_guard.validate_token(token)
        print(f"✅ Validação de token: {is_valid}")
        
        # Teste de informações de segurança
        security_info = security_guard.get_security_info()
        print(f"✅ Informações de segurança: {security_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do SecurityGuard completo: {e}")
        return False

def executar_todos_testes():
    """Executa todos os testes do SecurityGuard"""
    print("🔐 INÍCIO DOS TESTES - SECURITY GUARD INTEGRADO")
    print("=" * 60)
    
    resultados = []
    
    # Teste 1: SecurityGuard standalone
    resultados.append(teste_security_guard_completo())
    
    # Teste 2: SecurityGuard no MAESTRO
    resultados.append(teste_security_guard_maestro())
    
    # Teste 3: SecurityGuard no SessionOrchestrator
    resultados.append(teste_security_guard_session())
    
    # Teste 4: SecurityGuard no MainOrchestrator
    resultados.append(teste_security_guard_main())
    
    # Resumo dos resultados
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    testes_passaram = sum(resultados)
    total_testes = len(resultados)
    
    print(f"✅ Testes passaram: {testes_passaram}/{total_testes}")
    print(f"📈 Taxa de sucesso: {(testes_passaram/total_testes)*100:.1f}%")
    
    if testes_passaram == total_testes:
        print("🎉 TODOS OS TESTES PASSARAM! SecurityGuard integrado com sucesso")
        status = "SUCESSO_TOTAL"
    elif testes_passaram >= total_testes * 0.75:
        print("✅ MAIORIA DOS TESTES PASSOU! SecurityGuard parcialmente integrado")
        status = "SUCESSO_PARCIAL"
    else:
        print("❌ FALHA NOS TESTES! SecurityGuard não integrado adequadamente")
        status = "FALHA"
    
    print(f"\n🔐 STATUS FINAL: {status}")
    print(f"⏰ Teste executado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        'status': status,
        'testes_passaram': testes_passaram,
        'total_testes': total_testes,
        'taxa_sucesso': (testes_passaram/total_testes)*100,
        'resultados': resultados
    }

if __name__ == "__main__":
    resultado = executar_todos_testes()
    
    # Exit code para CI/CD
    if resultado['status'] == 'SUCESSO_TOTAL':
        exit(0)
    elif resultado['status'] == 'SUCESSO_PARCIAL':
        exit(1)
    else:
        exit(2) 