"""
🧪 TESTE REAL DE INTEGRAÇÃO - Verificação Completa

Teste prático para verificar se TODA a arquitetura modular
está realmente integrada e funcionando.
"""

import sys
import os
import asyncio
import traceback
from typing import Dict, Any

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_imports():
    """Testa se todos os imports estão funcionando."""
    print("🔍 TESTE 1: Verificando imports...")
    
    errors = []
    
    try:
        # Import principal
        from app.claude_ai_novo import ClaudeAINovo, IntegrationManager
        print("✅ Imports principais: OK")
    except Exception as e:
        errors.append(f"❌ Import principal falhou: {e}")
        print(f"❌ Import principal falhou: {e}")
    
    try:
        # Multi-agent imports
        from app.claude_ai_novo.multi_agent.system import MultiAgentSystem
        from app.claude_ai_novo.multi_agent.multi_agent_orchestrator import MultiAgentOrchestrator
        print("✅ Multi-agent imports: OK")
    except Exception as e:
        errors.append(f"❌ Multi-agent imports falharam: {e}")
        print(f"❌ Multi-agent imports falharam: {e}")
    
    try:
        # Database imports
        from app.claude_ai_novo.semantic.readers.database_reader import DatabaseReader
        from app.claude_ai_novo.semantic.readers.database import (
            DatabaseConnection, MetadataReader, DataAnalyzer
        )
        print("✅ Database imports: OK")
    except Exception as e:
        errors.append(f"❌ Database imports falharam: {e}")
        print(f"❌ Database imports falharam: {e}")
    
    try:
        # Agent imports individuais
        from app.claude_ai_novo.multi_agent.agents.entregas_agent import EntregasAgent
        from app.claude_ai_novo.multi_agent.agents.fretes_agent import FretesAgent
        print("✅ Agents imports: OK")
    except Exception as e:
        errors.append(f"❌ Agents imports falharam: {e}")
        print(f"❌ Agents imports falharam: {e}")
    
    return len(errors) == 0, errors

def test_module_creation():
    """Testa se os módulos podem ser criados."""
    print("\n🏗️ TESTE 2: Criação de módulos...")
    
    errors = []
    modules_created = {}
    
    try:
        # DatabaseConnection
        from app.claude_ai_novo.semantic.readers.database.database_connection import DatabaseConnection
        db_conn = DatabaseConnection()
        modules_created['database_connection'] = True
        print("✅ DatabaseConnection criado")
    except Exception as e:
        errors.append(f"❌ DatabaseConnection falhou: {e}")
        modules_created['database_connection'] = False
        print(f"❌ DatabaseConnection falhou: {e}")
    
    try:
        # EntregasAgent
        from app.claude_ai_novo.multi_agent.agents.entregas_agent import EntregasAgent
        agent = EntregasAgent()
        modules_created['entregas_agent'] = True
        print("✅ EntregasAgent criado")
    except Exception as e:
        errors.append(f"❌ EntregasAgent falhou: {e}")
        modules_created['entregas_agent'] = False
        print(f"❌ EntregasAgent falhou: {e}")
    
    try:
        # IntegrationManager
        from app.claude_ai_novo.integration_manager import IntegrationManager
        integration = IntegrationManager()
        modules_created['integration_manager'] = True
        print("✅ IntegrationManager criado")
    except Exception as e:
        errors.append(f"❌ IntegrationManager falhou: {e}")
        modules_created['integration_manager'] = False
        print(f"❌ IntegrationManager falhou: {e}")
    
    return len(errors) == 0, errors, modules_created

async def test_integration_manager():
    """Testa o Integration Manager completo."""
    print("\n🔗 TESTE 3: Integration Manager completo...")
    
    try:
        from app.claude_ai_novo.integration_manager import IntegrationManager
        
        # Criar integration manager
        integration = IntegrationManager()
        print("✅ IntegrationManager instanciado")
        
        # Testar inicialização (sem dependências externas)
        result = await integration.initialize_all_modules()
        print(f"✅ Inicialização executada: {result.get('success', False)}")
        print(f"📊 Módulos carregados: {result.get('modules_loaded', 0)}")
        print(f"📊 Módulos ativos: {result.get('modules_active', 0)}")
        print(f"📊 Módulos falharam: {result.get('modules_failed', 0)}")
        
        # Testar status
        status = integration.get_system_status()
        print(f"📊 Status do sistema: {status.get('total_modules', 0)} módulos")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Integration Manager falhou: {e}")
        print(traceback.format_exc())
        return False, str(e)

async def test_claude_ai_novo():
    """Testa a classe principal ClaudeAINovo."""
    print("\n🚀 TESTE 4: Claude AI Novo completo...")
    
    try:
        from app.claude_ai_novo import ClaudeAINovo
        
        # Criar instância
        claude_ai = ClaudeAINovo()
        print("✅ ClaudeAINovo instanciado")
        
        # Testar inicialização
        result = await claude_ai.initialize_system()
        print(f"✅ Sistema inicializado: {result.get('success', False)}")
        print(f"📊 Sistema pronto: {result.get('ready_for_operation', False)}")
        
        # Testar status
        status = claude_ai.get_system_status()
        print(f"📊 Status completo obtido: {len(status)} campos")
        
        # Testar módulos disponíveis
        modules = claude_ai.get_available_modules()
        print(f"📊 Módulos disponíveis: {len(modules)}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ ClaudeAINovo falhou: {e}")
        print(traceback.format_exc())
        return False, str(e)

def test_file_structure():
    """Testa se a estrutura de arquivos está correta."""
    print("\n📁 TESTE 5: Estrutura de arquivos...")
    
    base_path = "app/claude_ai_novo"
    required_files = [
        "__init__.py",
        "integration_manager.py",
        "multi_agent/system.py",
        "multi_agent/multi_agent_orchestrator.py",
        "multi_agent/agents/__init__.py",
        "multi_agent/agents/entregas_agent.py",
        "semantic/readers/database_reader.py",
        "semantic/readers/database/__init__.py",
        "semantic/readers/database/database_connection.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - AUSENTE")
            missing_files.append(file_path)
    
    return len(missing_files) == 0, missing_files

async def run_all_tests():
    """Executa todos os testes."""
    print("🧪 INICIANDO VERIFICAÇÃO COMPLETA DE INTEGRAÇÃO")
    print("=" * 60)
    
    all_results = {}
    
    # Teste 1: Imports
    imports_ok, import_errors = test_imports()
    all_results['imports'] = {'success': imports_ok, 'errors': import_errors}
    
    # Teste 2: Criação de módulos
    creation_ok, creation_errors, modules = test_module_creation()
    all_results['module_creation'] = {'success': creation_ok, 'errors': creation_errors, 'modules': modules}
    
    # Teste 3: Integration Manager
    integration_ok, integration_result = await test_integration_manager()
    all_results['integration_manager'] = {'success': integration_ok, 'result': integration_result}
    
    # Teste 4: Claude AI Novo
    claude_ok, claude_result = await test_claude_ai_novo()
    all_results['claude_ai_novo'] = {'success': claude_ok, 'result': claude_result}
    
    # Teste 5: Estrutura de arquivos
    files_ok, missing_files = test_file_structure()
    all_results['file_structure'] = {'success': files_ok, 'missing': missing_files}
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO FINAL DOS TESTES:")
    print("=" * 60)
    
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results.values() if result['success'])
    
    for test_name, result in all_results.items():
        status = "✅ PASSOU" if result['success'] else "❌ FALHOU"
        print(f"{test_name.upper()}: {status}")
        
        if not result['success']:
            if 'errors' in result:
                for error in result['errors'][:3]:  # Mostrar apenas primeiros 3 erros
                    print(f"  - {error}")
            if 'missing' in result:
                for missing in result['missing'][:3]:
                    print(f"  - Ausente: {missing}")
    
    print(f"\n🎯 RESULTADO GERAL: {passed_tests}/{total_tests} testes passaram")
    
    if passed_tests == total_tests:
        print("🎉 SISTEMA COMPLETAMENTE INTEGRADO E FUNCIONAL!")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️ SISTEMA MAJORITARIAMENTE FUNCIONAL - pequenos ajustes necessários")
    else:
        print("❌ SISTEMA PRECISA DE CORREÇÕES SIGNIFICATIVAS")
    
    return all_results, passed_tests / total_tests

if __name__ == "__main__":
    print("🚀 Executando teste de integração...")
    results, success_rate = asyncio.run(run_all_tests())
    print(f"\n📈 Taxa de sucesso: {success_rate:.1%}") 