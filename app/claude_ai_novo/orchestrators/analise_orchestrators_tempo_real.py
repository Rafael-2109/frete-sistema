#!/usr/bin/env python3
"""
Análise dos Orchestrators em Tempo Real
=======================================

Este arquivo executa uma análise completa dos orchestrators
e gera relatório detalhado de funcionalidade e eficiência.
"""
import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any, List

# Configurar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analisar_init_orchestrators():
    """Analisa o __init__.py dos orchestrators"""
    print("🔍 Analisando __init__.py dos orchestrators...")
    
    try:
        from __init__ import diagnose_orchestrator_module
        
        diagnostico = diagnose_orchestrator_module()
        
        print(f"   📊 Componentes carregados: {diagnostico['components_loaded']}")
        print(f"   📊 Total de componentes: {diagnostico['total_components']}")
        print(f"   📊 Status arquitetural: {diagnostico['architecture_status']}")
        
        for problema in diagnostico['problems']:
            if problema.startswith('✅'):
                print(f"   {problema}")
            elif problema.startswith('⚠️'):
                print(f"   {problema}")
            else:
                print(f"   {problema}")
        
        return {
            'sucesso': True,
            'componentes': diagnostico['total_components'],
            'problemas': len([p for p in diagnostico['problems'] if p.startswith('❌')]),
            'warnings': len([p for p in diagnostico['problems'] if p.startswith('⚠️')]),
            'detalhes': diagnostico
        }
        
    except Exception as e:
        print(f"   ❌ Erro na análise do __init__.py: {e}")
        return {'sucesso': False, 'erro': str(e)}

def analisar_orchestrator_manager():
    """Analisa o OrchestratorManager em tempo real"""
    print("🎭 Analisando OrchestratorManager (MAESTRO)...")
    
    try:
        from orchestrator_manager import get_orchestrator_manager
        
        start_time = time.time()
        manager = get_orchestrator_manager()
        init_time = time.time() - start_time
        
        print(f"   ⏱️ Tempo de inicialização: {init_time:.3f}s")
        
        # Status dos orquestradores
        start_time = time.time()
        status = manager.get_orchestrator_status()
        status_time = time.time() - start_time
        
        print(f"   ⏱️ Tempo de status: {status_time:.3f}s")
        print(f"   📊 Total de orquestradores: {status['total_orchestrators']}")
        print(f"   📊 Tarefas ativas: {status['active_tasks']}")
        print(f"   📊 Histórico: {status['operation_history_count']}")
        
        # Teste de detecção
        start_time = time.time()
        session_detect = manager._detect_appropriate_orchestrator("create_session", {"user": "test"})
        workflow_detect = manager._detect_appropriate_orchestrator("execute_workflow", {"workflow": "test"})
        detect_time = time.time() - start_time
        
        print(f"   ⏱️ Tempo de detecção: {detect_time:.3f}s")
        print(f"   🔍 Detecção para sessão: {session_detect.value}")
        print(f"   🔍 Detecção para workflow: {workflow_detect.value}")
        
        # Teste de operação
        start_time = time.time()
        result = manager.orchestrate_operation("test_operation", {"teste": "dados"})
        operation_time = time.time() - start_time
        
        print(f"   ⏱️ Tempo de operação: {operation_time:.3f}s")
        print(f"   ✅ Operação de teste: {result['success']}")
        
        return {
            'sucesso': True,
            'tempo_inicializacao': init_time,
            'tempo_status': status_time,
            'tempo_deteccao': detect_time,
            'tempo_operacao': operation_time,
            'total_orquestradores': status['total_orchestrators'],
            'detalhes': status
        }
        
    except Exception as e:
        print(f"   ❌ Erro no OrchestratorManager: {e}")
        return {'sucesso': False, 'erro': str(e)}

def analisar_main_orchestrator():
    """Analisa o MainOrchestrator em tempo real"""
    print("🎯 Analisando MainOrchestrator...")
    
    try:
        from main_orchestrator import MainOrchestrator
        
        start_time = time.time()
        orchestrator = MainOrchestrator()
        init_time = time.time() - start_time
        
        print(f"   ⏱️ Tempo de inicialização: {init_time:.3f}s")
        
        # Teste de workflows
        workflows = ["analyze_query", "full_processing", "intelligent_coordination", "natural_commands"]
        resultados = {}
        
        for workflow in workflows:
            start_time = time.time()
            result = orchestrator.execute_workflow(workflow, "test_operation", {"query": "teste"})
            exec_time = time.time() - start_time
            
            print(f"   ⏱️ Workflow {workflow}: {exec_time:.3f}s")
            print(f"   ✅ Resultado: {result['success']}")
            
            resultados[workflow] = {
                'sucesso': result['success'],
                'tempo_execucao': exec_time,
                'detalhes': result
            }
        
        # Verificar integrações
        coord_disponivel = orchestrator.coordinator_manager is not None
        cmd_disponivel = orchestrator.auto_command_processor is not None
        sec_disponivel = orchestrator.security_guard is not None
        
        print(f"   🔗 CoordinatorManager: {'✅' if coord_disponivel else '❌'}")
        print(f"   🔗 AutoCommandProcessor: {'✅' if cmd_disponivel else '❌'}")
        print(f"   🔗 SecurityGuard: {'✅' if sec_disponivel else '❌'}")
        
        return {
            'sucesso': True,
            'tempo_inicializacao': init_time,
            'workflows': resultados,
            'integracoes': {
                'coordinator_manager': coord_disponivel,
                'auto_command_processor': cmd_disponivel,
                'security_guard': sec_disponivel
            }
        }
        
    except Exception as e:
        print(f"   ❌ Erro no MainOrchestrator: {e}")
        return {'sucesso': False, 'erro': str(e)}

def analisar_session_orchestrator():
    """Analisa o SessionOrchestrator em tempo real"""
    print("🔄 Analisando SessionOrchestrator...")
    
    try:
        from session_orchestrator import get_session_orchestrator
        
        start_time = time.time()
        orchestrator = get_session_orchestrator()
        init_time = time.time() - start_time
        
        print(f"   ⏱️ Tempo de inicialização: {init_time:.3f}s")
        
        # Teste de sessão completa
        start_time = time.time()
        session_id = orchestrator.create_session(user_id=1, metadata={"teste": "tempo_real"})
        create_time = time.time() - start_time
        
        print(f"   ⏱️ Criação de sessão: {create_time:.3f}s")
        print(f"   ✅ Sessão criada: {session_id}")
        
        # Inicializar
        start_time = time.time()
        init_result = orchestrator.initialize_session(session_id)
        init_session_time = time.time() - start_time
        
        print(f"   ⏱️ Inicialização: {init_session_time:.3f}s")
        print(f"   ✅ Inicializada: {init_result}")
        
        # Workflow
        start_time = time.time()
        workflow_result = orchestrator.execute_session_workflow(session_id, "test_workflow", {"data": "teste"})
        workflow_time = time.time() - start_time
        
        print(f"   ⏱️ Workflow: {workflow_time:.3f}s")
        print(f"   ✅ Workflow executado: {workflow_result.get('success', 'N/A')}")
        
        # Completar
        start_time = time.time()
        complete_result = orchestrator.complete_session(session_id)
        complete_time = time.time() - start_time
        
        print(f"   ⏱️ Completar: {complete_time:.3f}s")
        print(f"   ✅ Completada: {complete_result}")
        
        # Verificar integrações
        learning_disponivel = orchestrator.learning_core is not None
        sec_disponivel = orchestrator.security_guard is not None
        
        print(f"   🔗 LearningCore: {'✅' if learning_disponivel else '❌'}")
        print(f"   🔗 SecurityGuard: {'✅' if sec_disponivel else '❌'}")
        
        return {
            'sucesso': True,
            'tempo_inicializacao': init_time,
            'tempo_criar_sessao': create_time,
            'tempo_inicializar': init_session_time,
            'tempo_workflow': workflow_time,
            'tempo_completar': complete_time,
            'integracoes': {
                'learning_core': learning_disponivel,
                'security_guard': sec_disponivel
            }
        }
        
    except Exception as e:
        print(f"   ❌ Erro no SessionOrchestrator: {e}")
        return {'sucesso': False, 'erro': str(e)}

def analisar_workflow_orchestrator():
    """Analisa o WorkflowOrchestrator em tempo real"""
    print("⚙️ Analisando WorkflowOrchestrator...")
    
    try:
        from workflow_orchestrator import WorkflowOrchestrator
        
        start_time = time.time()
        orchestrator = WorkflowOrchestrator()
        init_time = time.time() - start_time
        
        print(f"   ⏱️ Tempo de inicialização: {init_time:.3f}s")
        
        # Teste de workflows
        templates = ["analise_completa", "processamento_lote"]
        resultados = {}
        
        for template in templates:
            start_time = time.time()
            result = orchestrator.executar_workflow(f"test_{template}", template, {"dados": "teste"})
            exec_time = time.time() - start_time
            
            print(f"   ⏱️ Template {template}: {exec_time:.3f}s")
            print(f"   ✅ Resultado: {result['sucesso']}")
            
            resultados[template] = {
                'sucesso': result['sucesso'],
                'tempo_execucao': exec_time,
                'detalhes': result
            }
        
        # Estatísticas
        stats = orchestrator.obter_estatisticas()
        print(f"   📊 Templates disponíveis: {len(stats['templates_disponiveis'])}")
        print(f"   📊 Executores registrados: {len(stats['executores_registrados'])}")
        
        return {
            'sucesso': True,
            'tempo_inicializacao': init_time,
            'templates': resultados,
            'estatisticas': stats
        }
        
    except Exception as e:
        print(f"   ❌ Erro no WorkflowOrchestrator: {e}")
        return {'sucesso': False, 'erro': str(e)}

def gerar_relatorio_completo():
    """Gera relatório completo da análise"""
    print("📋 Gerando relatório completo...")
    
    relatorio = {
        'timestamp': datetime.now().isoformat(),
        'analise_init': analisar_init_orchestrators(),
        'orchestrator_manager': analisar_orchestrator_manager(),
        'main_orchestrator': analisar_main_orchestrator(),
        'session_orchestrator': analisar_session_orchestrator(),
        'workflow_orchestrator': analisar_workflow_orchestrator()
    }
    
    # Salvar relatório
    nome_arquivo = f"relatorio_orchestrators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Relatório salvo em: {nome_arquivo}")
    
    return relatorio

def exibir_resumo_executivo(relatorio: Dict[str, Any]):
    """Exibe resumo executivo da análise"""
    print("\n" + "="*60)
    print("📊 RESUMO EXECUTIVO - ANÁLISE DOS ORCHESTRATORS")
    print("="*60)
    
    # Contar sucessos
    sucessos = sum([
        relatorio['analise_init']['sucesso'],
        relatorio['orchestrator_manager']['sucesso'],
        relatorio['main_orchestrator']['sucesso'],
        relatorio['session_orchestrator']['sucesso'],
        relatorio['workflow_orchestrator']['sucesso']
    ])
    
    total_testes = 5
    taxa_sucesso = (sucessos / total_testes) * 100
    
    print(f"🎯 Taxa de Sucesso: {taxa_sucesso:.1f}% ({sucessos}/{total_testes})")
    
    # Tempos de inicialização
    tempos_init = []
    if relatorio['orchestrator_manager']['sucesso']:
        tempos_init.append(relatorio['orchestrator_manager']['tempo_inicializacao'])
    if relatorio['main_orchestrator']['sucesso']:
        tempos_init.append(relatorio['main_orchestrator']['tempo_inicializacao'])
    if relatorio['session_orchestrator']['sucesso']:
        tempos_init.append(relatorio['session_orchestrator']['tempo_inicializacao'])
    if relatorio['workflow_orchestrator']['sucesso']:
        tempos_init.append(relatorio['workflow_orchestrator']['tempo_inicializacao'])
    
    if tempos_init:
        tempo_medio = sum(tempos_init) / len(tempos_init)
        print(f"⏱️ Tempo Médio de Inicialização: {tempo_medio:.3f}s")
    
    # Status dos componentes
    if relatorio['analise_init']['sucesso']:
        print(f"📊 Componentes Carregados: {relatorio['analise_init']['componentes']}")
    
    if relatorio['orchestrator_manager']['sucesso']:
        print(f"📊 Orquestradores Ativos: {relatorio['orchestrator_manager']['total_orquestradores']}")
    
    # Integrações
    if relatorio['main_orchestrator']['sucesso']:
        integracoes = relatorio['main_orchestrator']['integracoes']
        print(f"🔗 Integrações MainOrchestrator: {sum(integracoes.values())}/3")
    
    if relatorio['session_orchestrator']['sucesso']:
        integracoes = relatorio['session_orchestrator']['integracoes']
        print(f"🔗 Integrações SessionOrchestrator: {sum(integracoes.values())}/2")
    
    # Avaliação final
    if taxa_sucesso >= 80:
        print("✅ AVALIAÇÃO: EXCELENTE - Sistema funcionando corretamente")
    elif taxa_sucesso >= 60:
        print("⚠️ AVALIAÇÃO: BOM - Algumas funcionalidades com problemas")
    else:
        print("❌ AVALIAÇÃO: CRÍTICO - Sistema com problemas sérios")

if __name__ == "__main__":
    print("🚀 ANÁLISE DOS ORCHESTRATORS EM TEMPO REAL")
    print("="*60)
    
    try:
        relatorio = gerar_relatorio_completo()
        exibir_resumo_executivo(relatorio)
        
    except Exception as e:
        print(f"❌ Erro crítico na análise: {e}")
        import traceback
        traceback.print_exc() 