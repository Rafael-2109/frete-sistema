#!/usr/bin/env python3
"""
🚀 TESTE DE PRODUÇÃO - Simula uso real do sistema
"""

import asyncio
import sys
import os

# Adicionar paths necessários
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

print("🚀 TESTE DE PRODUÇÃO - SISTEMA CLAUDE AI NOVO")
print("=" * 60)

async def testar_consultas_reais():
    """Testa consultas reais como no sistema web"""
    
    try:
        from app.claude_ai_novo import ClaudeAINovo
        
        # Inicializar sistema
        claude_ai = ClaudeAINovo()
        
        print("📱 Inicializando sistema...")
        await claude_ai.initialize_system()
        
        # Consultas reais que usuários fazem
        consultas_teste = [
            "Como estão as entregas do Atacadão hoje?",
            "Quantas entregas estão pendentes?", 
            "Status das entregas de São Paulo",
            "Quais clientes têm problemas de entrega?",
            "Relatório de entregas atrasadas"
        ]
        
        print(f"\n🎯 Testando {len(consultas_teste)} consultas reais:")
        print("=" * 60)
        
        sucessos = 0
        for i, consulta in enumerate(consultas_teste, 1):
            print(f"\n{i}️⃣ CONSULTA: '{consulta}'")
            
            try:
                # Processar consulta (como no sistema web)
                resultado = await claude_ai.process_query(consulta, {})
                
                if resultado.get('success'):
                    agent_response = resultado.get('agent_response', {})
                    
                    # Verificar se há resposta dos agentes
                    if agent_response and agent_response.get('response'):
                        print(f"   ✅ SUCESSO: Resposta gerada ({len(agent_response.get('response', ''))} chars)")
                        sucessos += 1
                    else:
                        print(f"   ⚠️ PARCIAL: Sistema funcionou mas sem resposta dos agentes")
                else:
                    print(f"   ❌ FALHA: {resultado.get('error', 'Erro desconhecido')}")
                    
            except Exception as e:
                print(f"   ❌ ERRO: {e}")
        
        print(f"\n📊 RESULTADO FINAL:")
        print(f"✅ Sucessos: {sucessos}/{len(consultas_teste)}")
        print(f"📈 Taxa de sucesso: {sucessos/len(consultas_teste)*100:.1f}%")
        
        if sucessos >= len(consultas_teste) * 0.8:  # 80% de sucesso
            print("🎉 SISTEMA FUNCIONANDO PERFEITAMENTE EM PRODUÇÃO!")
        else:
            print("⚠️ Sistema precisa de ajustes adicionais")
            
    except Exception as e:
        print(f"❌ Erro crítico no teste de produção: {e}")
        import traceback
        traceback.print_exc()

# Executar teste
asyncio.run(testar_consultas_reais()) 