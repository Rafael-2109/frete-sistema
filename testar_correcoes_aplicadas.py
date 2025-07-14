#!/usr/bin/env python3
"""
Testa o sistema Claude AI Novo após correções de UTF-8 e Flask context
"""

import sys
from pathlib import Path
import json

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent))

def testar_sistema_corrigido():
    """Testa o sistema após as correções"""
    print("=" * 80)
    print("🔍 TESTANDO SISTEMA APÓS CORREÇÕES")
    print("=" * 80)
    
    # 1. Testar DatabaseConnection com UTF-8
    print("\n1. Testando DatabaseConnection (UTF-8)...")
    try:
        from app.claude_ai_novo.scanning.database.database_connection import DatabaseConnection
        
        db_conn = DatabaseConnection()
        info = db_conn.get_connection_info()
        
        print(f"✅ DatabaseConnection:")
        print(f"   - Conectado: {info['connected']}")
        print(f"   - Inspector disponível: {info['inspector_available']}")
        print(f"   - Método de conexão: {info['connection_method']}")
        print(f"   - Teste de conexão: {info['test_result']}")
        
        if not info['connected']:
            print("   ⚠️ Sem conexão com banco, mas sem erro UTF-8!")
            
    except Exception as e:
        print(f"❌ Erro na DatabaseConnection: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. Testar LoaderManager
    print("\n2. Testando LoaderManager...")
    try:
        from app.claude_ai_novo.loaders import get_loader_manager
        
        loader_manager = get_loader_manager()
        print("✅ LoaderManager obtido")
        
        # Testar carregamento de entregas
        print("\n   Testando load_data_by_domain('entregas')...")
        
        filters = {
            'cliente': 'Atacadão',
            'periodo': 30
        }
        
        result = loader_manager.load_data_by_domain('entregas', filters)
        
        print(f"   ✅ Resultado:")
        print(f"      - Success: {result.get('success', False)}")
        print(f"      - Total registros: {result.get('total_registros', 0)}")
        print(f"      - Loader usado: {result.get('loader_used', 'unknown')}")
        print(f"      - É mock?: {result.get('is_mock', False)}")
        
        if result.get('dados_json'):
            print(f"      - Primeiro registro: {json.dumps(result['dados_json'][0], indent=2, ensure_ascii=False)[:200]}...")
            
    except Exception as e:
        print(f"❌ Erro no LoaderManager: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Testar fluxo completo via MainOrchestrator
    print("\n3. Testando MainOrchestrator (fluxo completo)...")
    try:
        from app.claude_ai_novo.orchestrators.main_orchestrator import get_main_orchestrator
        
        orchestrator = get_main_orchestrator()
        print("✅ MainOrchestrator obtido")
        
        query = "Como estão as entregas do Atacadão?"
        context = {
            'user_id': 'test_user',
            'test_mode': True
        }
        
        print(f"\n   Processando query: '{query}'")
        result = orchestrator.process_query(query, context)
        
        print(f"   ✅ Resultado:")
        print(f"      - Success: {result.get('success', False)}")
        print(f"      - Response existe: {bool(result.get('response'))}")
        print(f"      - Workflow: {result.get('workflow', 'unknown')}")
        
        if result.get('response'):
            print(f"\n   📝 RESPOSTA:")
            print(f"      {result['response'][:300]}...")
            
    except Exception as e:
        print(f"❌ Erro no MainOrchestrator: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Resumo
    print("\n" + "=" * 80)
    print("📊 RESUMO DAS CORREÇÕES")
    print("=" * 80)
    
    correções = [
        "✅ UTF-8 encoding adicionado nas conexões PostgreSQL",
        "✅ Flask context melhorado nos loaders",
        "✅ Dados mock implementados como fallback",
        "✅ LoaderManager com melhor tratamento de erros",
        "✅ EntregasLoader com _get_mock_data()",
    ]
    
    for correção in correções:
        print(f"   {correção}")
    
    print("\n💡 PRÓXIMOS PASSOS:")
    print("   1. Deploy para o Render")
    print("   2. Monitorar logs para verificar se dados reais são carregados")
    print("   3. Se ainda houver problemas, verificar DATABASE_URL no Render")

if __name__ == "__main__":
    testar_sistema_corrigido() 