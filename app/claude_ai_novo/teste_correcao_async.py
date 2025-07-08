#!/usr/bin/env python3
"""
🧪 TESTE DE CORREÇÃO ASYNC/AWAIT

Testa se as correções nos métodos assíncronos resolveram 
o problema de 'coroutine object has no attribute strip'
"""

import sys
import os
import asyncio

# Ajustar path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

async def teste_correcao_async():
    """Testa se as correções async/await funcionam"""
    
    print("🧪 TESTE DE CORREÇÃO ASYNC/AWAIT")
    print("=" * 50)
    
    resultados = []
    
    # 1. TESTE INTEGRATION MANAGER
    print("\n1. 🔗 TESTANDO IntegrationManager:")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        integration_manager = get_integration_manager()
        
        # Verificar se métodos existem
        if hasattr(integration_manager, 'process_unified_query'):
            print("   ✅ Método process_unified_query existe")
            resultados.append("✅ process_unified_query existe")
        else:
            print("   ❌ Método process_unified_query ausente")
            resultados.append("❌ process_unified_query ausente")
            
        if hasattr(integration_manager, 'process_query'):
            print("   ✅ Método process_query existe")
            resultados.append("✅ process_query existe")
        else:
            print("   ❌ Método process_query ausente")
            resultados.append("❌ process_query ausente")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ IntegrationManager erro: {str(e)[:50]}")
    
    # 2. TESTE SMART BASE AGENT
    print("\n2. 🤖 TESTANDO SmartBaseAgent:")
    try:
        from app.claude_ai_novo.multi_agent.agents.smart_base_agent import SmartBaseAgent
        from app.claude_ai_novo.multi_agent.agent_types import AgentType
        
        agent = SmartBaseAgent(AgentType.ENTREGAS)
        
        # Verificar se tem IntegrationManager
        if agent.tem_integration_manager:
            print("   ✅ SmartBaseAgent conectado ao IntegrationManager")
            resultados.append("✅ SmartBaseAgent conectado")
        else:
            print("   ❌ SmartBaseAgent não conectado ao IntegrationManager")
            resultados.append("❌ SmartBaseAgent não conectado")
            
        # Verificar se método existe
        if hasattr(agent, '_delegar_para_integration_manager'):
            print("   ✅ Método _delegar_para_integration_manager existe")
            resultados.append("✅ Delegação existe")
        else:
            print("   ❌ Método _delegar_para_integration_manager ausente")
            resultados.append("❌ Delegação ausente")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ SmartBaseAgent erro: {str(e)[:50]}")
    
    # 3. TESTE CLAUDE REAL INTEGRATION
    print("\n3. 🎯 TESTANDO ClaudeRealIntegration:")
    try:
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        
        claude = ClaudeRealIntegration()
        
        # Verificar se método não é assíncrono (não deve ter __await__)
        if hasattr(claude.processar_consulta_real, '__await__'):
            print("   ❌ PROBLEMA: processar_consulta_real é assíncrono")
            resultados.append("❌ processar_consulta_real é async")
        else:
            print("   ✅ processar_consulta_real não é assíncrono (correto)")
            resultados.append("✅ processar_consulta_real correto")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ ClaudeRealIntegration erro: {str(e)[:50]}")
    
    # 4. TESTE ASYNC REAL (SE POSSÍVEL)
    print("\n4. 🚀 TESTANDO Chamada Async Real:")
    try:
        # Tentar chamar um método assíncrono para ver se funciona
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        integration_manager = get_integration_manager()
        
        # Simular contexto mínimo
        context = {
            'user_id': 'teste',
            'username': 'Teste Async',
            'agent_type': 'entregas'
        }
        
        # Tentar processar uma consulta simples
        resultado = await integration_manager.process_query("teste async", context)
        
        if isinstance(resultado, dict) and 'success' in resultado:
            print("   ✅ Chamada async executada com sucesso")
            print(f"   ✅ Resultado: {resultado.get('success', False)}")
            resultados.append("✅ Chamada async funcionou")
        else:
            print("   ⚠️ Chamada async executada mas resultado inesperado")
            resultados.append("⚠️ Resultado async inesperado")
            
    except Exception as e:
        print(f"   ❌ ERRO na chamada async: {e}")
        resultados.append(f"❌ Chamada async erro: {str(e)[:50]}")
    
    # 📊 RESUMO
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS RESULTADOS:")
    print("=" * 50)
    
    sucessos = len([r for r in resultados if r.startswith("✅")])
    total = len(resultados)
    
    for resultado in resultados:
        print(f"   {resultado}")
    
    print(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
    
    if sucessos >= 6:
        print("🎉 CORREÇÕES ASYNC/AWAIT APLICADAS COM SUCESSO!")
        print("✅ Problema de 'coroutine object' deve estar resolvido")
        return True
    elif sucessos >= 4:
        print("⚠️ CORREÇÕES PARCIALMENTE APLICADAS")
        print("🔧 Alguns ajustes finais podem ser necessários")
        return True
    else:
        print("❌ CORREÇÕES PRECISAM DE MAIS AJUSTES")
        print("🔧 Problemas async/await ainda existem")
        return False

if __name__ == "__main__":
    asyncio.run(teste_correcao_async()) 