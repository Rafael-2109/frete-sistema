#!/usr/bin/env python3
"""
Testa o fluxo completo do sistema Claude AI Novo após correções
"""

import sys
from pathlib import Path
import json
import asyncio

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent))

def testar_fluxo_completo():
    """Testa o fluxo completo desde a query até a resposta"""
    print("=" * 80)
    print("🔍 TESTANDO FLUXO COMPLETO DO SISTEMA CLAUDE AI NOVO")
    print("=" * 80)
    
    # 1. Importar componentes principais
    print("\n1. Importando componentes...")
    try:
        from app.claude_ai_novo.orchestrators.main_orchestrator import get_main_orchestrator
        from app.claude_ai_novo.analyzers import get_analyzer_manager
        from app.claude_ai_novo.loaders import get_loader_manager
        
        print("✅ Componentes importados com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        return False
    
    # 2. Obter instâncias
    print("\n2. Obtendo instâncias...")
    try:
        orchestrator = get_main_orchestrator()
        analyzer = get_analyzer_manager()
        loader = get_loader_manager()
        
        print("✅ Instâncias obtidas")
    except Exception as e:
        print(f"❌ Erro ao obter instâncias: {e}")
        return False
    
    # 3. Testar analyze_query
    print("\n3. Testando AnalyzerManager...")
    query = "Como estão as entregas do Atacadão dos últimos 30 dias?"
    try:
        analysis = analyzer.analyze_query(query)
        print(f"✅ Análise concluída:")
        print(f"   - Components used: {analysis.get('components_used', [])}")
        print(f"   - Domains: {analysis.get('semantic_analysis', {}).get('domains', [])}")
        print(f"   - Intent: {analysis.get('intention_analysis', {}).get('intention', 'unknown')}")
        
        # Verificar se domains existe
        semantic_analysis = analysis.get('semantic_analysis', {})
        if semantic_analysis and 'domains' in semantic_analysis:
            domains = semantic_analysis['domains']
            print(f"   ✅ Domains retornados: {domains}")
        else:
            print("   ❌ Campo 'domains' não encontrado na análise!")
            
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Testar LoaderManager
    print("\n4. Testando LoaderManager...")
    try:
        # Pegar domínio da análise
        domain = None
        if 'semantic_analysis' in analysis and 'domains' in analysis['semantic_analysis']:
            domains = analysis['semantic_analysis']['domains']
            if domains:
                domain = domains[0]
        
        if not domain:
            domain = 'entregas'  # Fallback
            
        print(f"   - Usando domínio: {domain}")
        
        # Carregar dados
        data = loader.load_data_by_domain(domain, {})
        print(f"✅ Dados carregados:")
        print(f"   - Tipo: {type(data)}")
        if isinstance(data, dict):
            print(f"   - Chaves: {list(data.keys())}")
            print(f"   - Total registros: {data.get('total', 0)}")
        
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Testar MainOrchestrator
    print("\n5. Testando MainOrchestrator...")
    try:
        # Context sem session_id para testar geração automática
        context = {
            'user_id': 'test_user',
            'test_mode': True
        }
        
        print("   - Processando query via MainOrchestrator...")
        result = orchestrator.process_query(query, context)
        
        print(f"✅ Resultado do MainOrchestrator:")
        print(f"   - Success: {result.get('success', False)}")
        print(f"   - Response length: {len(result.get('response', ''))}")
        print(f"   - Workflow: {result.get('workflow', 'unknown')}")
        
        # Verificar se session_id foi gerado
        if 'data' in result and 'session_id' in result['data']:
            print(f"   ✅ Session ID gerado: {result['data']['session_id']}")
        
        # Verificar resposta
        if result.get('response'):
            print(f"\n📝 RESPOSTA FINAL (primeiros 200 chars):")
            print(f"   {result['response'][:200]}...")
        else:
            print("   ❌ Nenhuma resposta gerada!")
            
    except Exception as e:
        print(f"❌ Erro no MainOrchestrator: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Verificar componentes usados
    print("\n6. Verificando componentes usados no workflow...")
    if 'steps_results' in result:
        steps = result['steps_results']
        print(f"✅ Steps executados: {list(steps.keys())}")
        
        # Verificar cada step
        for step_name, step_result in steps.items():
            if isinstance(step_result, dict) and 'error' in step_result:
                print(f"   ❌ {step_name}: ERRO - {step_result['error']}")
            else:
                print(f"   ✅ {step_name}: OK")
    
    print("\n" + "=" * 80)
    print("📊 RESUMO DO TESTE")
    print("=" * 80)
    
    # Verificar problemas conhecidos
    problemas = []
    
    # Verificar domains
    if not (analysis.get('semantic_analysis', {}).get('domains')):
        problemas.append("AnalyzerManager não retorna 'domains'")
    
    # Verificar session_id
    if result and 'data' in result and 'session_id' not in result['data']:
        problemas.append("Session ID não foi gerado")
    
    # Verificar resposta
    if not result.get('response'):
        problemas.append("Nenhuma resposta foi gerada")
    
    if problemas:
        print("❌ PROBLEMAS ENCONTRADOS:")
        for p in problemas:
            print(f"   - {p}")
    else:
        print("✅ TODOS OS TESTES PASSARAM!")
    
    return len(problemas) == 0

if __name__ == "__main__":
    sucesso = testar_fluxo_completo()
    
    if sucesso:
        print("\n✅ FLUXO COMPLETO FUNCIONANDO!")
    else:
        print("\n❌ FLUXO COM PROBLEMAS - VERIFICAR LOGS ACIMA") 