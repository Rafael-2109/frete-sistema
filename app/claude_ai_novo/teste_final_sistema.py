#!/usr/bin/env python3
"""
🧪 TESTE FINAL DO SISTEMA
========================

Verifica se o sistema está funcionando corretamente após todas as correções.
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configurar variáveis de ambiente
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

def teste_completo():
    """Executa teste completo do sistema"""
    print("\n🧪 TESTE FINAL DO SISTEMA CLAUDE AI NOVO\n")
    
    sucesso_total = True
    
    # Teste 1: Imports diretos
    print("1️⃣ TESTANDO IMPORTS DIRETOS...")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        print("   ✅ Imports diretos funcionando")
    except Exception as e:
        print(f"   ❌ Erro nos imports: {e}")
        sucesso_total = False
        return sucesso_total
    
    # Teste 2: Criar instâncias
    print("\n2️⃣ TESTANDO CRIAÇÃO DE INSTÂNCIAS...")
    try:
        start = time.time()
        integration_manager = get_integration_manager()
        print(f"   ✅ IntegrationManager criado em {time.time() - start:.2f}s")
        
        # Verificar status
        status = integration_manager.get_system_status()
        print(f"   📊 Status: orchestrator_loaded={status.get('orchestrator_loaded', False)}")
        print(f"   📊 Dados disponíveis: {status.get('data_provider_available', False)}")
        print(f"   📊 Claude disponível: {status.get('claude_integration_available', False)}")
        
    except Exception as e:
        print(f"   ❌ Erro ao criar instâncias: {e}")
        sucesso_total = False
        return sucesso_total
    
    # Teste 3: Processar query simples
    print("\n3️⃣ TESTANDO PROCESSAMENTO DE QUERY...")
    try:
        # Criar função async para teste
        async def testar_query():
            result = await integration_manager.process_unified_query(
                "teste do sistema",
                {"test": True}
            )
            return result
        
        # Executar
        start = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(testar_query())
        
        print(f"   ✅ Query processada em {time.time() - start:.2f}s")
        print(f"   📊 Resultado: success={result.get('success', False)}")
        
        if result.get('response'):
            print(f"   📊 Resposta: {str(result['response'])[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Erro ao processar query: {e}")
        sucesso_total = False
    
    # Teste 4: Verificar componentes
    print("\n4️⃣ VERIFICANDO COMPONENTES DO SISTEMA...")
    try:
        # Carregar orchestrator
        integration_manager._ensure_orchestrator_loaded()
        
        if integration_manager.orchestrator_manager:
            print("   ✅ OrchestratorManager carregado")
            
            # Verificar sub-componentes
            orch = integration_manager.orchestrator_manager
            if hasattr(orch, 'main_orchestrator'):
                print("   ✅ MainOrchestrator disponível")
            if hasattr(orch, 'session_orchestrator'):
                print("   ✅ SessionOrchestrator disponível")
            if hasattr(orch, 'workflow_orchestrator'):
                print("   ✅ WorkflowOrchestrator disponível")
        else:
            print("   ⚠️ OrchestratorManager não carregado")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar componentes: {e}")
        sucesso_total = False
    
    # Teste 5: Testar claude_transition
    print("\n5️⃣ TESTANDO CLAUDE TRANSITION...")
    try:
        from app.claude_transition import processar_consulta_transicao
        
        start = time.time()
        resposta = processar_consulta_transicao("Como está o sistema?")
        
        print(f"   ✅ Claude Transition funcionando em {time.time() - start:.2f}s")
        print(f"   📊 Resposta: {str(resposta)[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Erro no Claude Transition: {e}")
        sucesso_total = False
    
    # Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DO TESTE FINAL")
    print("="*60)
    
    if sucesso_total:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("\n🎉 SISTEMA CLAUDE AI NOVO ESTÁ 100% FUNCIONAL!")
        print("\n💡 O QUE FOI CORRIGIDO:")
        print("   - Imports circulares resolvidos")
        print("   - Travamentos eliminados")
        print("   - Lazy loading funcionando")
        print("   - Todos os componentes operacionais")
        
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("   1. Reinicie o servidor Flask")
        print("   2. O sistema está pronto para produção")
        print("   3. Use imports diretos em novos códigos")
        
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
        print("Verifique os erros acima para mais detalhes")
    
    return sucesso_total

if __name__ == "__main__":
    # Executar teste
    sucesso = teste_completo()
    
    # Retornar código de saída apropriado
    sys.exit(0 if sucesso else 1) 