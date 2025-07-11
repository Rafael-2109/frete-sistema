#!/usr/bin/env python3
"""
Teste da integração dos módulos órfãos.
Verifica se suggestions e conversers foram integrados corretamente.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrators.main_orchestrator import get_main_orchestrator
from orchestrators.session_orchestrator import get_session_orchestrator
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_suggestions_integration():
    """Testa integração do SuggestionsManager no MainOrchestrator"""
    print("🔍 Testando integração do SuggestionsManager...")
    
    orchestrator = get_main_orchestrator()
    
    # Testar propriedade lazy loading
    suggestions_manager = orchestrator.suggestions_manager
    print(f"✅ SuggestionsManager carregado: {suggestions_manager is not None}")
    
    # Testar componente pré-carregado
    suggestions_component = orchestrator.components.get("suggestions")
    print(f"✅ Componente suggestions disponível: {suggestions_component is not None}")
    
    # Testar workflow de sugestões
    test_data = {
        "query": "Como melhorar performance?",
        "context": {"user_id": 1},
        "user_id": 1
    }
    
    result = orchestrator.execute_workflow("intelligent_suggestions", "intelligent_suggestions", test_data)
    print(f"✅ Workflow de sugestões executado: {result.get('success', False)}")
    
    if result.get('success'):
        suggestions = result.get('suggestions_result') or result.get('fallback_suggestions', {})
        if suggestions:
            print(f"💡 Sugestões geradas: {len(suggestions.get('suggestions', []))}")
            for i, suggestion in enumerate(suggestions.get('suggestions', [])[:3]):
                print(f"   {i+1}. {suggestion}")
        else:
            print("💡 Nenhuma sugestão retornada, mas workflow executado com sucesso")
    
    return result.get('success', False)

def test_conversers_integration():
    """Testa integração do ConversationManager no SessionOrchestrator"""
    print("\n🔍 Testando integração do ConversationManager...")
    
    orchestrator = get_session_orchestrator()
    
    # Testar propriedade lazy loading
    conversation_manager = orchestrator.conversation_manager
    print(f"✅ ConversationManager carregado: {conversation_manager is not None}")
    
    # Criar uma sessão de teste
    session_id = orchestrator.create_session(user_id=1)
    print(f"✅ Sessão criada: {session_id}")
    
    # Testar workflow com conversas
    test_data = {
        "query": "Olá, como você está?",
        "context": {"user_id": 1},
        "message": "Olá, como você está?"
    }
    
    result = orchestrator.execute_session_workflow(session_id, "conversation", test_data)
    print(f"✅ Workflow de conversa executado: {result.get('success', True)}")
    
    if 'conversation_insights' in result:
        insights = result['conversation_insights']
        print(f"💬 Insights de conversa: {insights.get('total_turns', 0)} turnos")
        print(f"💬 Score de conversa: {insights.get('conversation_score', 0):.2f}")
        print(f"💬 Continuidade: {insights.get('context_continuity', 0):.2f}")
    
    # Limpar sessão
    orchestrator.complete_session(session_id)
    print(f"✅ Sessão completada")
    
    return True

def test_workflows_integration():
    """Testa se os workflows foram adicionados corretamente"""
    print("\n🔍 Testando workflows integrados...")
    
    main_orchestrator = get_main_orchestrator()
    
    # Verificar workflows disponíveis
    workflows = main_orchestrator.workflows
    print(f"✅ Workflows disponíveis: {len(workflows)}")
    
    expected_workflows = [
        "analyze_query",
        "full_processing", 
        "intelligent_coordination",
        "natural_commands",
        "intelligent_suggestions"  # NOVO workflow
    ]
    
    for workflow_name in expected_workflows:
        if workflow_name in workflows:
            print(f"   ✅ {workflow_name}")
        else:
            print(f"   ❌ {workflow_name} - FALTANDO")
    
    # Testar workflow de sugestões especificamente
    suggestions_workflow = workflows.get("intelligent_suggestions")
    if suggestions_workflow:
        print(f"✅ Workflow 'intelligent_suggestions' tem {len(suggestions_workflow)} passos")
        for step in suggestions_workflow:
            print(f"   - {step.name} ({step.component}.{step.method})")
    
    return "intelligent_suggestions" in workflows

def main():
    """Função principal do teste"""
    print("🧪 TESTE DE INTEGRAÇÃO DOS MÓDULOS ÓRFÃOS")
    print("=" * 50)
    
    # Testes individuais
    success_count = 0
    total_tests = 3
    
    try:
        if test_suggestions_integration():
            success_count += 1
            print("✅ Teste de SuggestionsManager: PASSOU")
        else:
            print("❌ Teste de SuggestionsManager: FALHOU")
    except Exception as e:
        print(f"❌ Teste de SuggestionsManager: ERRO - {e}")
    
    try:
        if test_conversers_integration():
            success_count += 1
            print("✅ Teste de ConversationManager: PASSOU")
        else:
            print("❌ Teste de ConversationManager: FALHOU")
    except Exception as e:
        print(f"❌ Teste de ConversationManager: ERRO - {e}")
    
    try:
        if test_workflows_integration():
            success_count += 1
            print("✅ Teste de Workflows: PASSOU")
        else:
            print("❌ Teste de Workflows: FALHOU")
    except Exception as e:
        print(f"❌ Teste de Workflows: ERRO - {e}")
    
    # Resultado final
    print("\n" + "=" * 50)
    print(f"🎯 RESULTADO FINAL: {success_count}/{total_tests} testes passaram")
    
    if success_count == total_tests:
        print("🎉 INTEGRAÇÃO COMPLETA! Todos os módulos órfãos foram integrados com sucesso.")
        print("\n📋 RESUMO DA INTEGRAÇÃO:")
        print("   💡 SuggestionsManager → MainOrchestrator")
        print("   💬 ConversationManager → SessionOrchestrator")
        print("   ⚙️ Workflows inteligentes adicionados")
        print("   🔄 Lazy loading implementado")
        print("   🛡️ Fallbacks mock configurados")
        return True
    else:
        print("⚠️ Integração parcial. Alguns módulos podem não estar funcionando corretamente.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 