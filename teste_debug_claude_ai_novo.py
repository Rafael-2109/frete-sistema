#!/usr/bin/env python3
"""
🔍 SCRIPT DE DEBUG COMPLETO - Claude AI Novo
============================================

Script para diagnosticar exatamente onde está quebrando o fluxo
"""

import os
import sys
import logging

# Configurar path para encontrar módulos
sys.path.insert(0, os.path.abspath('.'))

from app.claude_transition import get_transition_manager
import asyncio

# Configurar logging para debug detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def testar_fluxo_completo():
    """Testa o fluxo completo passo a passo"""
    
    print("🔍 INICIANDO TESTE DE DEBUG COMPLETO")
    print("=" * 50)
    
    try:
        # 1. Teste do transition manager
        print("\n1️⃣ TESTANDO TRANSITION MANAGER")
        manager = get_transition_manager()
        print(f"✅ TransitionManager carregado: {manager is not None}")
        
        # 2. Teste query simples
        query = "Como estão as entregas do Atacadão?"
        print(f"\n2️⃣ TESTANDO QUERY: '{query}'")
        
        # Processar query
        result = await manager.processar_consulta(query)
        
        print(f"✅ Resultado obtido: {type(result)}")
        print(f"📊 Resultado: {str(result)[:500]}...")
        
        # 3. Teste componentes individuais
        print("\n3️⃣ TESTANDO COMPONENTES INDIVIDUAIS")
        
        # Testar analyzers
        try:
            from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
            analyzer_manager = get_analyzer_manager()
            
            if analyzer_manager:
                analysis = analyzer_manager.analyze_query(query)
                print(f"✅ Analyzer funcionando: {analysis.get('domains', [])}")
            else:
                print("❌ AnalyzerManager não disponível")
        except Exception as e:
            print(f"❌ Erro no analyzer: {e}")
        
        # Testar loaders
        try:
            from app.claude_ai_novo.loaders.loader_manager import get_loader_manager
            loader_manager = get_loader_manager()
            
            if loader_manager:
                # Testar carregamento de entregas
                data = loader_manager.load_data_by_domain("entregas", {"cliente": "atacadao"})
                print(f"✅ Loader funcionando: {data.get('total_registros', 0)} registros")
            else:
                print("❌ LoaderManager não disponível")
        except Exception as e:
            print(f"❌ Erro no loader: {e}")
        
        # Testar orchestrators
        try:
            from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
            orchestrator_manager = get_orchestrator_manager()
            
            if orchestrator_manager:
                # Testar processamento
                orch_result = await orchestrator_manager.process_query(query)
                print(f"✅ Orchestrator funcionando: {orch_result.get('success', False)}")
            else:
                print("❌ OrchestratorManager não disponível")
        except Exception as e:
            print(f"❌ Erro no orchestrator: {e}")
        
        return result
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        return None

async def testar_steps_workflow():
    """Testa cada step do workflow individualmente"""
    
    print("\n\n4️⃣ TESTANDO STEPS DO WORKFLOW INDIVIDUALMENTE")
    print("=" * 50)
    
    query = "Como estão as entregas do Atacadão?"
    
    # Step 1: Analyze Query
    try:
        from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
        analyzer = get_analyzer_manager()
        
        if analyzer:
            analysis = analyzer.analyze_query(query)
            print(f"✅ STEP 1 - Analyze Query:")
            print(f"   Domínios detectados: {analysis.get('query_analysis', {}).get('domains', [])}")
            print(f"   Tipo de consulta: {analysis.get('query_analysis', {}).get('query_type', 'unknown')}")
        else:
            print("❌ STEP 1 - Analyzer não disponível")
    except Exception as e:
        print(f"❌ STEP 1 - Erro: {e}")
    
    # Step 2: Load Data
    try:
        from app.claude_ai_novo.loaders.loader_manager import get_loader_manager
        loader = get_loader_manager()
        
        if loader:
            data = loader.load_data_by_domain("entregas", {"cliente": "atacadao"})
            print(f"✅ STEP 2 - Load Data:")
            print(f"   Registros encontrados: {data.get('total_registros', 0)}")
            print(f"   Sucesso: {data.get('success', False)}")
            print(f"   Erro: {data.get('erro', 'Nenhum')}")
        else:
            print("❌ STEP 2 - Loader não disponível")
    except Exception as e:
        print(f"❌ STEP 2 - Erro: {e}")
    
    # Step 3: Generate Response
    try:
        from app.claude_ai_novo.processors.response_processor import get_response_processor
        processor = get_response_processor()
        
        if processor:
            # Dados mock para teste
            mock_analysis = {"domains": ["entregas"], "entities": {"empresa": ["atacadao"]}}
            mock_data = {"dados_json": [], "total_registros": 0}
            
            response = processor.gerar_resposta_otimizada(
                consulta=query,
                analise=mock_analysis,
                user_context={},
                dados_reais=mock_data
            )
            print(f"✅ STEP 3 - Generate Response:")
            print(f"   Resposta gerada: {str(response)[:200]}...")
        else:
            print("❌ STEP 3 - ResponseProcessor não disponível")
    except Exception as e:
        print(f"❌ STEP 3 - Erro: {e}")

if __name__ == "__main__":
    # Executar testes
    asyncio.run(testar_fluxo_completo())
    asyncio.run(testar_steps_workflow())
    
    print("\n\n🎯 TESTE CONCLUÍDO!")
    print("Analise os resultados acima para identificar onde está o problema.") 