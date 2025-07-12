#!/usr/bin/env python3
"""
Script para testar a integração melhorada dos módulos
"""

import logging
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def testar_enrichers():
    """Testa o EnricherManager"""
    print("\n🔍 TESTANDO ENRICHERS")
    print("=" * 50)
    
    try:
        from enrichers import get_enricher_manager
        
        manager = get_enricher_manager()
        if manager:
            print("✅ EnricherManager carregado")
            
            # Testar enriquecimento
            dados_teste = {
                'entregas': [
                    {'status': 'entregue', 'no_prazo': True},
                    {'status': 'entregue', 'no_prazo': False},
                    {'status': 'pendente', 'no_prazo': None}
                ]
            }
            
            resultado = manager.enrich_context(
                data=dados_teste,
                query="Como estão as entregas?",
                domain="entregas"
            )
            
            print(f"✅ Dados enriquecidos com {len(resultado)} campos")
            
            # Verificar campos adicionados
            campos_novos = [k for k in resultado.keys() if k not in dados_teste]
            print(f"✅ Campos adicionados: {campos_novos}")
            
            # Verificar análise
            if 'analise_entregas' in resultado:
                analise = resultado['analise_entregas']
                print(f"✅ Taxa de sucesso: {analise.get('taxa_sucesso', 0):.1f}%")
            
            return True
        else:
            print("❌ EnricherManager não disponível")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar enrichers: {e}")
        return False

def testar_memorizers():
    """Testa o MemoryManager"""
    print("\n🧠 TESTANDO MEMORIZERS")
    print("=" * 50)
    
    try:
        from memorizers import get_memory_manager
        
        manager = get_memory_manager()
        if manager:
            print("✅ MemoryManager carregado")
            
            session_id = f"test_session_{datetime.now().timestamp()}"
            
            # Testar get_context
            context = manager.get_context(session_id)
            print(f"✅ Contexto obtido: {list(context.keys())}")
            
            # Testar save_interaction
            success = manager.save_interaction(
                session_id=session_id,
                query="Teste de pergunta",
                response="Teste de resposta"
            )
            print(f"✅ Interação salva: {success}")
            
            # Verificar se foi salvo
            context_novo = manager.get_context(session_id)
            if 'historico' in context_novo:
                print(f"✅ Histórico atualizado: {len(context_novo['historico'])} mensagens")
            
            return True
        else:
            print("❌ MemoryManager não disponível")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar memorizers: {e}")
        return False

def testar_workflow_integrado():
    """Testa o workflow integrado com enrichers e memorizers"""
    print("\n🔄 TESTANDO WORKFLOW INTEGRADO")
    print("=" * 50)
    
    try:
        from orchestrators import get_main_orchestrator
        
        orchestrator = get_main_orchestrator()
        if orchestrator:
            print("✅ MainOrchestrator carregado")
            
            # Dados de teste
            data = {
                'query': 'Quantas entregas do Atacadão estão pendentes?',
                'session_id': f'test_{datetime.now().timestamp()}',
                'context': {
                    'user': 'teste',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Executar workflow
            print("\n📊 Executando workflow response_processing...")
            resultado = orchestrator.execute_workflow(
                workflow_name="response_processing",
                operation_type="response_processing",
                data=data
            )
            
            if resultado.get('success'):
                print("✅ Workflow executado com sucesso")
                
                # Verificar steps executados
                steps_executados = [k for k in resultado.keys() if k.endswith('_result')]
                print(f"✅ Steps executados: {len(steps_executados)}")
                
                # Verificar memória
                if 'load_memory_result' in resultado:
                    print("✅ Memória carregada no início")
                
                # Verificar enriquecimento
                if 'enrich_data_result' in resultado:
                    print("✅ Dados enriquecidos")
                    enrich_result = resultado['enrich_data_result']
                    if isinstance(enrich_result, dict) and 'metadata' in enrich_result:
                        print("✅ Metadados adicionados")
                
                # Verificar salvamento
                if 'save_memory_result' in resultado:
                    print("✅ Interação salva na memória")
                
                return True
            else:
                print(f"❌ Workflow falhou: {resultado.get('error')}")
                return False
        else:
            print("❌ MainOrchestrator não disponível")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar workflow: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_integracao_modulos():
    """Verifica integração de todos os módulos"""
    print("\n📊 VERIFICANDO INTEGRAÇÃO DOS MÓDULOS")
    print("=" * 50)
    
    try:
        from orchestrators import get_main_orchestrator
        
        orchestrator = get_main_orchestrator()
        components = orchestrator.components
        
        print(f"\n✅ Componentes registrados: {len(components)}")
        
        # Verificar componentes essenciais
        essenciais = [
            'analyzers', 'processors', 'enrichers', 'memorizers',
            'providers', 'validators', 'mappers', 'loaders'
        ]
        
        for comp in essenciais:
            if comp in components:
                print(f"✅ {comp}: {type(components[comp]).__name__}")
            else:
                print(f"❌ {comp}: NÃO REGISTRADO")
        
        # Verificar workflows
        workflows = orchestrator.workflows
        print(f"\n✅ Workflows disponíveis: {len(workflows)}")
        for wf_name, steps in workflows.items():
            print(f"  - {wf_name}: {len(steps)} steps")
            
    except Exception as e:
        print(f"❌ Erro ao verificar integração: {e}")

def main():
    """Função principal"""
    print("🚀 TESTE DE INTEGRAÇÃO MELHORADA DOS MÓDULOS")
    print("=" * 70)
    
    resultados = {
        'enrichers': testar_enrichers(),
        'memorizers': testar_memorizers(),
        'workflow': testar_workflow_integrado()
    }
    
    # Verificar integração geral
    verificar_integracao_modulos()
    
    # Resumo
    print("\n📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    total = len(resultados)
    sucesso = sum(1 for v in resultados.values() if v)
    
    for modulo, resultado in resultados.items():
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{modulo}: {status}")
    
    print(f"\nTotal: {sucesso}/{total} testes passaram ({sucesso/total*100:.0f}%)")
    
    if sucesso == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! Integração funcionando perfeitamente.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima.")

if __name__ == "__main__":
    main() 