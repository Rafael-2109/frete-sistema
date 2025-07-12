"""
Script de teste para verificar extração de resposta do sistema Claude AI Novo
"""

import asyncio
import json
import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configurar para usar o sistema novo
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

from app.claude_transition import get_transition_manager

async def test_response_extraction():
    """Testa a extração de resposta do sistema novo."""
    
    print("🧪 Testando extração de resposta do Claude AI Novo...")
    print("-" * 60)
    
    # Obter o manager de transição
    manager = get_transition_manager()
    print(f"✅ Sistema ativo: {manager.sistema_ativo}")
    
    # Testar com uma consulta simples
    test_queries = [
        "teste",
        "Como estão as entregas do Atacadão?",
        "Quantos pedidos temos hoje?"
    ]
    
    for query in test_queries:
        print(f"\n📝 Testando query: '{query}'")
        
        try:
            # Processar consulta
            result = await manager.processar_consulta(query)
            
            print(f"📊 Tipo de resultado: {type(result)}")
            
            if isinstance(result, dict):
                print(f"🔍 Estrutura do resultado:")
                print(json.dumps(result, indent=2, ensure_ascii=False)[:500] + "...")
            else:
                print(f"📄 Resultado direto: {result}")
            
            # Verificar se é uma resposta vazia
            if result == "{}" or result == {} or not result:
                print("❌ PROBLEMA: Resposta vazia detectada!")
            else:
                print("✅ Resposta não está vazia")
                
        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "-" * 60)
    print("🏁 Teste concluído")

if __name__ == "__main__":
    asyncio.run(test_response_extraction()) 