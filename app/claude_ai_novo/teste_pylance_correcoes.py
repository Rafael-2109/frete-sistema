#!/usr/bin/env python3
"""
🧪 TESTE DE CORREÇÕES PYLANCE

Testa se as correções async/await resolveram os erros:
- Argument of type "Coroutine[Any, Any, str]" cannot be assigned
- Expression of type "Coroutine[Any, Any, str]" is incompatible
"""

import sys
import os
import asyncio
import inspect

# Ajustar path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

async def teste_pylance_correcoes():
    """Testa se as correções de tipos async/await funcionam"""
    
    print("🧪 TESTE DE CORREÇÕES PYLANCE")
    print("=" * 50)
    
    resultados = []
    
    # 1. TESTE CLAUDE REAL INTEGRATION
    print("\n1. 🎯 TESTANDO ClaudeRealIntegration:")
    try:
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        
        claude = ClaudeRealIntegration()
        
        # Verificar se método é assíncrono
        metodo = claude.processar_consulta_real
        is_async = inspect.iscoroutinefunction(metodo)
        
        print(f"   📋 Método processar_consulta_real é async: {is_async}")
        
        if is_async:
            print("   ⚠️ MÉTODO É ASYNC - deve usar await")
            resultados.append("⚠️ processar_consulta_real é async")
        else:
            print("   ✅ MÉTODO É SYNC - não precisa await")
            resultados.append("✅ processar_consulta_real é sync")
            
        # Testar se tem atributo __await__
        has_await = hasattr(metodo, '__await__')
        print(f"   📋 Tem atributo __await__: {has_await}")
        
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ ClaudeRealIntegration erro: {str(e)[:50]}")
    
    # 2. TESTE INTEGRATION MANAGER
    print("\n2. 🔗 TESTANDO IntegrationManager:")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        manager = get_integration_manager()
        
        # Verificar se métodos são assíncronos
        process_query_async = inspect.iscoroutinefunction(manager.process_query)
        process_unified_async = inspect.iscoroutinefunction(manager.process_unified_query)
        
        print(f"   📋 process_query é async: {process_query_async}")
        print(f"   📋 process_unified_query é async: {process_unified_async}")
        
        if process_query_async and process_unified_async:
            print("   ✅ Métodos são async (correto)")
            resultados.append("✅ IntegrationManager métodos async")
        else:
            print("   ❌ Métodos não são async")
            resultados.append("❌ IntegrationManager métodos não async")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ IntegrationManager erro: {str(e)[:50]}")
    
    # 3. TESTE CLAUDE TRANSITION
    print("\n3. 🔄 TESTANDO ClaudeTransition:")
    try:
        from app.claude_transition import get_claude_transition
        
        transition = get_claude_transition()
        
        # Verificar se método é assíncrono
        processar_async = inspect.iscoroutinefunction(transition.processar_consulta)
        
        print(f"   📋 processar_consulta é async: {processar_async}")
        print(f"   📋 Sistema ativo: {transition.sistema_ativo}")
        
        if processar_async:
            print("   ✅ Método processar_consulta é async (correto)")
            resultados.append("✅ ClaudeTransition async")
        else:
            print("   ❌ Método processar_consulta não é async")
            resultados.append("❌ ClaudeTransition não async")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ ClaudeTransition erro: {str(e)[:50]}")
    
    # 4. TESTE SIMULADO DE TYPES
    print("\n4. 🔍 TESTANDO Tipos de Retorno:")
    try:
        # Simular teste de tipos como o Pylance faria
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        
        claude = ClaudeRealIntegration()
        
        # Simular chamada
        if inspect.iscoroutinefunction(claude.processar_consulta_real):
            print("   ⚠️ PROBLEMA: processar_consulta_real retorna Coroutine")
            print("   🔧 SOLUÇÃO: Deve usar await para obter str")
            resultados.append("⚠️ Tipo Coroutine detectado")
        else:
            print("   ✅ processar_consulta_real retorna str diretamente")
            resultados.append("✅ Tipo str correto")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ Teste tipos erro: {str(e)[:50]}")
    
    # 5. TESTE REAL DE CHAMADAS
    print("\n5. 🚀 TESTANDO Chamadas Reais:")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        manager = get_integration_manager()
        
        # Contexto de teste
        context = {
            'user_id': 'teste_pylance',
            'username': 'Teste Correções'
        }
        
        # Testar process_query
        resultado = await manager.process_query("teste correções async", context)
        
        if isinstance(resultado, dict):
            response = resultado.get('response', '')
            if isinstance(response, str):
                print("   ✅ process_query retorna str corretamente")
                resultados.append("✅ Chamada real funcionou")
            else:
                print(f"   ❌ process_query retorna tipo incorreto: {type(response)}")
                resultados.append("❌ Tipo retorno incorreto")
        else:
            print(f"   ❌ Resultado inesperado: {type(resultado)}")
            resultados.append("❌ Resultado inesperado")
            
    except Exception as e:
        print(f"   ❌ ERRO na chamada real: {e}")
        resultados.append(f"❌ Chamada real erro: {str(e)[:50]}")
    
    # 📊 RESUMO
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS RESULTADOS:")
    print("=" * 50)
    
    sucessos = len([r for r in resultados if r.startswith("✅")])
    total = len(resultados)
    
    for resultado in resultados:
        print(f"   {resultado}")
    
    print(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
    
    # ANÁLISE PYLANCE
    print("\n" + "=" * 50)
    print("🔍 ANÁLISE PYLANCE:")
    print("=" * 50)
    
    if sucessos >= 4:
        print("🎉 CORREÇÕES PYLANCE APLICADAS COM SUCESSO!")
        print("✅ Tipos async/await corrigidos")
        print("✅ Erros 'Coroutine cannot be assigned' devem estar resolvidos")
        print("✅ IntegrationManager usando await corretamente")
        print("✅ ClaudeTransition com verificação de tipos")
        return True
    elif sucessos >= 2:
        print("⚠️ CORREÇÕES PARCIALMENTE APLICADAS")
        print("🔧 Alguns erros Pylance podem persistir")
        return True
    else:
        print("❌ CORREÇÕES PYLANCE PRECISAM DE MAIS AJUSTES")
        print("🔧 Erros de tipos async/await ainda existem")
        return False

if __name__ == "__main__":
    asyncio.run(teste_pylance_correcoes()) 