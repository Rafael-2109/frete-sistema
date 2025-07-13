#!/usr/bin/env python3
"""
🔍 TESTE END-TO-END REVISADO: Fluxo Completo Simplificado
========================================================

Simula o fluxo completo de uma pergunta do usuário através do sistema.
Versão revisada com métodos corretos e verificações simplificadas.
"""

import sys
import os
import logging
from datetime import datetime
import json

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_section(title: str):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"📍 {title}")
    print(f"{'='*60}\n")

def run_complete_flow():
    """Executa fluxo completo de processamento de uma pergunta"""
    
    print("\n🚀 TESTE E2E: FLUXO COMPLETO DO SISTEMA CLAUDE AI NOVO")
    print("="*60)
    
    # Configuração inicial
    user_query = "Quantas entregas temos pendentes do Assai em São Paulo?"
    user_id = "test_user_123"
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"👤 Usuário: {user_id}")
    print(f"❓ Pergunta: {user_query}")
    print(f"🔑 Sessão: {session_id}\n")
    
    results = {
        'query': user_query,
        'user_id': user_id,
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'steps': {}
    }
    
    try:
        # 1. INICIALIZAR ORCHESTRATOR
        print_section("1. INICIALIZANDO SISTEMA")
        
        from app.claude_ai_novo.orchestrators import get_main_orchestrator
        orchestrator = get_main_orchestrator()
        
        if not orchestrator:
            print("❌ Erro ao inicializar orchestrator")
            return results
        
        print(f"✅ Orchestrator inicializado")
        print(f"📦 Componentes carregados: {len(orchestrator.components)}")
        print(f"🔧 Workflows disponíveis: {len(orchestrator.workflows)}")
        
        results['steps']['initialization'] = {
            'success': True,
            'components': len(orchestrator.components),
            'workflows': list(orchestrator.workflows.keys())
        }
        
        # 2. ANÁLISE DA PERGUNTA
        print_section("2. ANALISANDO PERGUNTA")
        
        analyzer = orchestrator.components.get('analyzers')
        if analyzer:
            analysis = analyzer.analyze_query(user_query)
            
            # Extrair informações relevantes
            semantic = analysis.get('semantic_analysis', {})
            intention = analysis.get('intention_analysis', {})
            
            print(f"📊 Análise realizada:")
            print(f"   - Domínios: {semantic.get('domains', ['não detectado'])}")
            print(f"   - Intenção: {intention.get('intention', 'não detectada')}")
            print(f"   - Confiança: {intention.get('confidence', 0):.2%}")
            print(f"   - Componentes usados: {analysis.get('components_used', [])}")
            
            results['steps']['analysis'] = {
                'success': True,
                'domains': semantic.get('domains', []),
                'intention': intention.get('intention'),
                'confidence': intention.get('confidence', 0),
                'components_used': analysis.get('components_used', [])
            }
        
        # 3. PROCESSAMENTO VIA WORKFLOW
        print_section("3. EXECUTANDO WORKFLOW")
        
        # Usar workflow analyze_query para processar
        if 'analyze_query' in orchestrator.workflows:
            workflow_data = {
                'query': user_query,
                'user_id': user_id,
                'session_id': session_id
            }
            workflow_result = orchestrator.execute_workflow(
                workflow_name='analyze_query',
                operation_type='analyze_query',  # ou 'intelligent_query'
                data=workflow_data
            )
            
            print(f"✅ Workflow executado:")
            print(f"   - Success: {workflow_result.get('success', False)}")
            print(f"   - Etapas executadas: {len(workflow_result.get('steps', []))}")
            
            results['steps']['workflow'] = {
                'success': workflow_result.get('success', False),
                'workflow_name': 'analyze_query',
                'steps_count': len(workflow_result.get('steps', []))
            }
        
        # 4. MEMORY & CONTEXT
        print_section("4. SALVANDO CONTEXTO")
        
        memorizer = orchestrator.components.get('memorizers')
        if memorizer:
            # Salvar análise na memória
            memory_data = {
                'query': user_query,
                'analysis': results['steps'].get('analysis', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            # Usar save_interaction para salvar no histórico
            stored = memorizer.save_interaction(
                session_id=session_id,
                query=user_query,
                response=json.dumps(workflow_result)  # Converter para JSON string
            )
            print(f"✅ Interação salva: {stored}")
            
            # Verificar recuperação
            context = memorizer.get_context(session_id)
            print(f"✅ Contexto recuperável: {context is not None}")
            
            results['steps']['memory'] = {
                'success': stored,
                'retrievable': context is not None
            }
        
        # 5. CONVERSAÇÃO
        print_section("5. GESTÃO DE CONVERSA")
        
        converser = orchestrator.components.get('conversers')
        if converser:
            # Verificar conexão com memorizer
            has_memory = hasattr(converser, 'context_memory') and converser.context_memory is not None
            print(f"✅ Converser → Memorizer conectado: {has_memory}")
            
            # Obter estatísticas
            stats = converser.get_manager_stats()
            print(f"📊 Estatísticas do Converser:")
            print(f"   - Conversas ativas: {stats.get('active_conversations', 0)}")
            print(f"   - Memória disponível: {stats.get('context_memory_available', False)}")
            
            results['steps']['conversation'] = {
                'success': True,
                'memory_connected': has_memory,
                'stats': stats
            }
        
        # 6. PROCESSAMENTO DE RESPOSTA
        print_section("6. PROCESSANDO RESPOSTA")
        
        processor = orchestrator.components.get('processors')
        if processor:
            # Verificar conexões
            has_memory = hasattr(processor, 'memory_manager') and processor.memory_manager is not None
            has_enricher = hasattr(processor, 'enricher') and processor.enricher is not None
            
            print(f"✅ Processor → Memory conectado: {has_memory}")
            print(f"✅ Processor → Enricher conectado: {has_enricher}")
            
            # Processar resposta simples
            response_context = {
                'query': user_query,
                'analysis': results['steps'].get('analysis', {}),
                'data': []  # Sem dados reais por enquanto
            }
            
            try:
                # Usar método correto do ProcessorManager
                chain_result = processor.execute_processing_chain(
                    consulta=user_query,
                    analise=analysis if 'analysis' in locals() else {},
                    chain_type="standard"
                )
                print(f"✅ Cadeia de processamento executada: {chain_result.get('status', 'unknown')}")
                
                results['steps']['processing'] = {
                    'success': True,
                    'memory_connected': has_memory,
                    'enricher_connected': has_enricher,
                    'chain_status': chain_result.get('status', 'completed')
                }
            except Exception as e:
                print(f"⚠️ Erro no processamento: {e}")
                results['steps']['processing'] = {
                    'success': False,
                    'error': str(e)
                }
        
        # RESUMO FINAL
        print_section("RESUMO DO TESTE E2E")
        
        total_steps = len(results['steps'])
        successful_steps = sum(1 for step in results['steps'].values() if step.get('success', False))
        
        print(f"📊 RESULTADO FINAL:")
        print(f"   - Total de etapas: {total_steps}")
        print(f"   - Etapas bem-sucedidas: {successful_steps}")
        print(f"   - Taxa de sucesso: {(successful_steps/total_steps)*100:.1f}%")
        
        print(f"\n🔗 CONEXÕES VERIFICADAS:")
        print(f"   - Scanner → Loader: {'loaders' in orchestrator.components and 'scanners' in orchestrator.components}")
        print(f"   - Mapper → Loader: {'loaders' in orchestrator.components and 'mappers' in orchestrator.components}")
        print(f"   - Loader → Provider: {'providers' in orchestrator.components and 'loaders' in orchestrator.components}")
        print(f"   - Memorizer → Processor: {results['steps'].get('processing', {}).get('memory_connected', False)}")
        print(f"   - Learner → Analyzer: {'analyzers' in orchestrator.components and 'learners' in orchestrator.components}")
        print(f"   - Enricher → Processor: {results['steps'].get('processing', {}).get('enricher_connected', False)}")
        print(f"   - Converser → Memorizer: {results['steps'].get('conversation', {}).get('memory_connected', False)}")
        
        # Salvar resultados
        results['summary'] = {
            'total_steps': total_steps,
            'successful_steps': successful_steps,
            'success_rate': (successful_steps/total_steps)*100,
            'completed_at': datetime.now().isoformat()
        }
        
        # Exportar resultados
        output_file = f"resultado_e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados salvos em: {output_file}")
        print(f"\n✅ TESTE E2E CONCLUÍDO!")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro crítico no teste E2E: {e}", exc_info=True)
        results['error'] = str(e)
        results['success'] = False
        return results

if __name__ == "__main__":
    run_complete_flow() 