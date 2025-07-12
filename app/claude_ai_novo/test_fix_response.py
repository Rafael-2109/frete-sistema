"""
Script para testar a correção do problema de resposta vazia "{}"
"""

import asyncio
import json
import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configurar para usar o sistema novo
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

async def test_fix():
    """Testa se a correção funcionou."""
    
    print("🔧 Testando correção do problema de resposta vazia...")
    print("=" * 60)
    
    # Importar após configurar a variável de ambiente
    from app.claude_transition import get_transition_manager
    
    # Obter o manager
    manager = get_transition_manager()
    print(f"✅ Sistema ativo: {manager.sistema_ativo}")
    
    # Testar consultas
    test_queries = [
        "teste",
        "Como estão as entregas do Atacadão?",
        "Quantos pedidos temos hoje?",
        "Status do sistema"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 40)
        
        try:
            # Processar
            result = await manager.processar_consulta(query)
            
            # Verificar tipo
            print(f"📊 Tipo: {type(result)}")
            
            # Verificar se é vazio
            if result == "{}" or result == {} or not result:
                print("❌ PROBLEMA: Resposta ainda está vazia!")
            else:
                print("✅ Resposta não está vazia")
                
                # Mostrar conteúdo
                if isinstance(result, str):
                    print(f"📄 Conteúdo: {result[:200]}...")
                else:
                    print(f"📄 Conteúdo: {json.dumps(result, ensure_ascii=False, indent=2)[:200]}...")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Teste concluído")

if __name__ == "__main__":
    asyncio.run(test_fix()) 