#!/usr/bin/env python3
"""
Testa a integração completa do CoordinatorManager
"""

import sys
from pathlib import Path

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent))

def testar_coordinator_manager():
    """Testa o CoordinatorManager e suas integrações"""
    print("=" * 60)
    print("🔍 TESTANDO COORDINATOR MANAGER")
    print("=" * 60)
    
    # 1. Importar e criar instância
    print("\n1. Importando CoordinatorManager...")
    try:
        from app.claude_ai_novo.coordinators.coordinator_manager import get_coordinator_manager
        manager = get_coordinator_manager()
        print("✅ CoordinatorManager importado e criado")
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        return False
    
    # 2. Verificar status
    print("\n2. Verificando status...")
    try:
        status = manager.get_coordinator_status()
        print(f"✅ Status obtido:")
        print(f"   - Inicializado: {status['initialized']}")
        print(f"   - Coordenadores: {status['coordinators_available']}")
        print(f"   - Domain Agents: {status['domain_agents_available']}")
        print(f"   - Total: {status['total_coordinators']}")
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")
        return False
    
    # 3. Testar cada tipo de coordenação
    test_queries = [
        # Domain agents
        ("Como estão as entregas do Atacadão?", "agent_entregas"),
        ("Quais os fretes pendentes?", "agent_fretes"),
        ("Status dos pedidos de hoje", "agent_pedidos"),
        
        # Intelligence
        ("Analise os padrões de entrega", "intelligence"),
        
        # Processor
        ("Processar workflow de entregas", "processor"),
        
        # Specialist (fallback)
        ("Consulta genérica", "specialist")
    ]
    
    print("\n3. Testando coordenações...")
    sucesso = 0
    for query, expected_coordinator in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            result = manager.coordinate_query(query)
            coordinator_used = result.get('coordinator_used', 'unknown')
            print(f"   ✅ Processado por: {coordinator_used}")
            
            if result.get('status') == 'success':
                sucesso += 1
                print(f"   ✅ Resultado: {result.get('result', {}).get('status', 'ok')}")
            else:
                print(f"   ⚠️ Status: {result.get('status')}")
                if result.get('message'):
                    print(f"   ⚠️ Mensagem: {result.get('message')}")
                    
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    # 4. Testar coordenação com contexto
    print("\n4. Testando com contexto...")
    try:
        context = {
            'user_id': 'test_user',
            'cliente_especifico': 'Atacadão',
            'periodo': 'últimos 30 dias'
        }
        result = manager.coordinate_query(
            "Status das entregas",
            context=context,
            preferred_coordinator='agent_entregas'
        )
        print(f"✅ Coordenação com contexto: {result.get('coordinator_used')}")
    except Exception as e:
        print(f"❌ Erro com contexto: {e}")
    
    # 5. Verificar métricas
    print("\n5. Verificando métricas...")
    try:
        final_status = manager.get_coordinator_status()
        metrics = final_status.get('performance_metrics', {})
        
        print("📊 Métricas de performance:")
        for coord_name, metric in metrics.items():
            if 'last_used' in metric:
                print(f"   - {coord_name}: usado {metric.get('queries_processed', metric.get('domain_queries', 0))} vezes")
    except Exception as e:
        print(f"❌ Erro ao verificar métricas: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTADO: {sucesso}/{len(test_queries)} testes bem-sucedidos")
    print(f"{'='*60}")
    
    return sucesso > len(test_queries) / 2  # Pelo menos metade funcionando

if __name__ == "__main__":
    sucesso = testar_coordinator_manager()
    
    if sucesso:
        print("\n✅ COORDINATOR MANAGER FUNCIONANDO!")
    else:
        print("\n❌ COORDINATOR MANAGER COM PROBLEMAS") 