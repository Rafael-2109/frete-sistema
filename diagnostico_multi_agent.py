#!/usr/bin/env python3
"""
Script de diagnóstico específico para Multi-Agent System
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('diagnostico_multi_agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Testa imports básicos"""
    logger.info("🔍 Testando imports...")
    
    try:
        from app.claude_ai.multi_agent_system import (
            MultiAgentSystem,
            AgentType,
            SpecialistAgent,
            CriticAgent
        )
        logger.info("✅ Imports básicos OK")
        return True
    except Exception as e:
        logger.error(f"❌ Erro nos imports: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_creation():
    """Testa criação de agentes"""
    logger.info("🔍 Testando criação de agentes...")
    
    try:
        from app.claude_ai.multi_agent_system import SpecialistAgent, AgentType
        
        # Criar agente sem Claude client
        agent = SpecialistAgent(AgentType.ENTREGAS, claude_client=None)
        logger.info("✅ Agente criado com sucesso")
        
        # Testar propriedades
        logger.info(f"Agent type: {agent.agent_type}")
        logger.info(f"Knowledge base: {type(agent.knowledge_base)}")
        logger.info(f"Specialist prompt: {len(agent.specialist_prompt)} chars")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erro na criação do agente: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_system_creation():
    """Testa criação do sistema multi-agente"""
    logger.info("🔍 Testando criação do sistema...")
    
    try:
        from app.claude_ai.multi_agent_system import MultiAgentSystem
        
        # Criar sistema sem Claude client
        system = MultiAgentSystem(claude_client=None)
        logger.info("✅ Sistema criado com sucesso")
        
        # Testar propriedades
        logger.info(f"Agents: {list(system.agents.keys())}")
        logger.info(f"Critic: {type(system.critic)}")
        logger.info(f"History: {len(system.operation_history)} operations")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erro na criação do sistema: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_process_query():
    """Testa processamento de consulta"""
    logger.info("🔍 Testando processamento de consulta...")
    
    try:
        from app.claude_ai.multi_agent_system import MultiAgentSystem
        
        # Criar sistema
        system = MultiAgentSystem(claude_client=None)
        
        # Processar consulta simples
        query = "teste simples"
        context = {"debug": True}
        
        logger.info(f"Processando: {query}")
        result = await system.process_query(query, context)
        
        logger.info(f"Resultado: {type(result)}")
        logger.info(f"Success: {result.get('success', False)}")
        
        if result.get('success'):
            logger.info("✅ Processamento bem-sucedido")
            logger.info(f"Response: {result.get('response', '')[:100]}...")
        else:
            logger.error(f"❌ Erro no processamento: {result.get('error', 'Unknown')}")
            
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"❌ Erro no processamento: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_response_convergence():
    """Testa convergência de respostas"""
    logger.info("🔍 Testando convergência de respostas...")
    
    try:
        from app.claude_ai.multi_agent_system import MultiAgentSystem
        
        system = MultiAgentSystem(claude_client=None)
        
        # Simular respostas de agentes
        mock_responses = [
            {
                'agent': 'entregas',
                'relevance': 0.8,
                'response': 'Resposta do agente entregas',
                'confidence': 0.9
            },
            {
                'agent': 'fretes',
                'relevance': 0.6,
                'response': 'Resposta do agente fretes',
                'confidence': 0.7
            }
        ]
        
        # Simular validação
        mock_validation = {
            'validation_score': 0.85,
            'approval': True,
            'inconsistencies': []
        }
        
        # Testar convergência
        result = await system._converge_responses(
            query="teste",
            agent_responses=mock_responses,
            validation_result=mock_validation
        )
        
        logger.info(f"Convergência: {type(result)}")
        logger.info(f"Resultado: {result[:100]}...")
        
        # Verificar se resultado não é None
        if result and isinstance(result, str):
            logger.info("✅ Convergência bem-sucedida")
            return True
        else:
            logger.error(f"❌ Convergência falhou: {type(result)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na convergência: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_edge_cases():
    """Testa casos extremos"""
    logger.info("🔍 Testando casos extremos...")
    
    try:
        from app.claude_ai.multi_agent_system import MultiAgentSystem
        
        system = MultiAgentSystem(claude_client=None)
        
        # Caso 1: Respostas None
        test_cases = [
            {
                'name': 'Respostas None',
                'responses': [
                    {'agent': 'test', 'response': None, 'relevance': 0.5, 'confidence': 0.5}
                ],
                'validation': {'validation_score': 1.0, 'approval': True}
            },
            {
                'name': 'Respostas vazias',
                'responses': [],
                'validation': {'validation_score': 1.0, 'approval': True}
            },
            {
                'name': 'Respostas mistas',
                'responses': [
                    {'agent': 'test1', 'response': 'Válida', 'relevance': 0.8, 'confidence': 0.9},
                    {'agent': 'test2', 'response': None, 'relevance': 0.5, 'confidence': 0.5}
                ],
                'validation': {'validation_score': 0.7, 'approval': True}
            }
        ]
        
        for test_case in test_cases:
            logger.info(f"Testando: {test_case['name']}")
            
            try:
                result = await system._converge_responses(
                    query="teste",
                    agent_responses=test_case['responses'],
                    validation_result=test_case['validation']
                )
                
                if result and isinstance(result, str):
                    logger.info(f"✅ {test_case['name']}: OK")
                else:
                    logger.error(f"❌ {test_case['name']}: FALHOU - {type(result)}")
                    
            except Exception as e:
                logger.error(f"❌ {test_case['name']}: ERRO - {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro nos testes extremos: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Função principal"""
    logger.info("🚀 Iniciando diagnóstico do Multi-Agent System...")
    
    tests = [
        ("Imports", test_imports),
        ("Agent Creation", test_agent_creation),
        ("System Creation", test_system_creation),
        ("Process Query", test_process_query),
        ("Response Convergence", test_response_convergence),
        ("Edge Cases", test_edge_cases)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTE: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            
        except Exception as e:
            logger.error(f"❌ Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Relatório final
    logger.info(f"\n{'='*60}")
    logger.info("RELATÓRIO FINAL")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    logger.info(f"📊 RESULTADOS: {passed}/{total} ({passed/total*100:.1f}%)")
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        logger.info(f"   {status}: {test_name}")
    
    if passed == total:
        logger.info("🎉 TODOS OS TESTES PASSARAM!")
    else:
        logger.warning(f"⚠️ {total - passed} testes falharam")
    
    logger.info(f"📋 Log completo salvo em: diagnostico_multi_agent.log")

if __name__ == "__main__":
    asyncio.run(main()) 