#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO - Problema com agent_type

Script para diagnosticar o problema específico com a propriedade agent_type
nos agentes de domínio.
"""

import logging
import traceback
import sys
import os
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adicionar path do sistema
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def testar_agent_type_issue():
    """Testa criação de agente e verifica propriedade agent_type"""
    
    resultados = {
        'testes_executados': 0,
        'sucessos': 0,
        'falhas': 0,
        'detalhes': []
    }
    
    # Teste 1: Importar AgentType
    try:
        from utils.agent_types import AgentType
        resultados['testes_executados'] += 1
        resultados['sucessos'] += 1
        resultados['detalhes'].append("✅ AgentType importado com sucesso")
        logger.info("✅ AgentType importado com sucesso")
    except Exception as e:
        resultados['testes_executados'] += 1
        resultados['falhas'] += 1
        resultados['detalhes'].append(f"❌ Erro ao importar AgentType: {e}")
        logger.error(f"❌ Erro ao importar AgentType: {e}")
        return resultados
    
    # Teste 2: Testar FretesAgent diretamente
    try:
        from coordinators.domain_agents.fretes_agent import FretesAgent
        
        # Criar instância do agente
        agent = FretesAgent()
        resultados['testes_executados'] += 1
        resultados['sucessos'] += 1
        resultados['detalhes'].append("✅ FretesAgent criado com sucesso")
        logger.info("✅ FretesAgent criado com sucesso")
        
        # Testar se tem agent_type
        if hasattr(agent, 'agent_type'):
            resultados['testes_executados'] += 1
            resultados['sucessos'] += 1
            resultados['detalhes'].append(f"✅ agent_type encontrado: {agent.agent_type}")
            logger.info(f"✅ agent_type encontrado: {agent.agent_type}")
            
            # Testar se agent_type tem value
            if hasattr(agent.agent_type, 'value'):
                resultados['testes_executados'] += 1
                resultados['sucessos'] += 1
                resultados['detalhes'].append(f"✅ agent_type.value: {agent.agent_type.value}")
                logger.info(f"✅ agent_type.value: {agent.agent_type.value}")
            else:
                resultados['testes_executados'] += 1
                resultados['falhas'] += 1
                resultados['detalhes'].append("❌ agent_type não tem propriedade 'value'")
                logger.error("❌ agent_type não tem propriedade 'value'")
        else:
            resultados['testes_executados'] += 1
            resultados['falhas'] += 1
            resultados['detalhes'].append("❌ FretesAgent não tem propriedade 'agent_type'")
            logger.error("❌ FretesAgent não tem propriedade 'agent_type'")
            
            # Listar todas as propriedades do agente
            propriedades = [attr for attr in dir(agent) if not attr.startswith('_')]
            resultados['detalhes'].append(f"📋 Propriedades do FretesAgent: {propriedades}")
            logger.info(f"📋 Propriedades do FretesAgent: {propriedades}")
            
    except Exception as e:
        resultados['testes_executados'] += 1
        resultados['falhas'] += 1
        resultados['detalhes'].append(f"❌ Erro ao criar FretesAgent: {e}")
        logger.error(f"❌ Erro ao criar FretesAgent: {e}")
        traceback.print_exc()
    
    # Teste 3: Testar todos os agentes
    agentes_para_testar = [
        ('FretesAgent', 'fretes_agent'),
        ('EntregasAgent', 'entregas_agent'),
        ('PedidosAgent', 'pedidos_agent'),
        ('EmbarquesAgent', 'embarques_agent'),
        ('FinanceiroAgent', 'financeiro_agent')
    ]
    
    for nome_classe, nome_modulo in agentes_para_testar:
        try:
            module = __import__(f'coordinators.domain_agents.{nome_modulo}', 
                              fromlist=[nome_classe])
            agent_class = getattr(module, nome_classe)
            
            # Criar instância
            agent = agent_class()
            resultados['testes_executados'] += 1
            
            # Verificar agent_type
            if hasattr(agent, 'agent_type'):
                resultados['sucessos'] += 1
                resultados['detalhes'].append(f"✅ {nome_classe} tem agent_type: {agent.agent_type}")
                logger.info(f"✅ {nome_classe} tem agent_type: {agent.agent_type}")
            else:
                resultados['falhas'] += 1
                resultados['detalhes'].append(f"❌ {nome_classe} não tem agent_type")
                logger.error(f"❌ {nome_classe} não tem agent_type")
                
        except Exception as e:
            resultados['testes_executados'] += 1
            resultados['falhas'] += 1
            resultados['detalhes'].append(f"❌ Erro ao testar {nome_classe}: {e}")
            logger.error(f"❌ Erro ao testar {nome_classe}: {e}")
    
    # Teste 4: Testar SpecialistAgent factory
    try:
        from coordinators.specialist_agents import SpecialistAgent
        
        # Criar via factory
        agent = SpecialistAgent(AgentType.FRETES)
        resultados['testes_executados'] += 1
        
        if hasattr(agent, 'agent_type'):
            resultados['sucessos'] += 1
            resultados['detalhes'].append(f"✅ SpecialistAgent factory tem agent_type: {agent.agent_type}")
            logger.info(f"✅ SpecialistAgent factory tem agent_type: {agent.agent_type}")
        else:
            resultados['falhas'] += 1
            resultados['detalhes'].append("❌ SpecialistAgent factory não tem agent_type")
            logger.error("❌ SpecialistAgent factory não tem agent_type")
            
    except Exception as e:
        resultados['testes_executados'] += 1
        resultados['falhas'] += 1
        resultados['detalhes'].append(f"❌ Erro ao testar SpecialistAgent factory: {e}")
        logger.error(f"❌ Erro ao testar SpecialistAgent factory: {e}")
    
    # Teste 5: Testar factory functions
    try:
        from coordinators.specialist_agents import create_fretes_agent
        
        # Criar via factory function
        agent = create_fretes_agent()
        resultados['testes_executados'] += 1
        
        if hasattr(agent, 'agent_type'):
            resultados['sucessos'] += 1
            resultados['detalhes'].append(f"✅ create_fretes_agent tem agent_type: {agent.agent_type}")
            logger.info(f"✅ create_fretes_agent tem agent_type: {agent.agent_type}")
        else:
            resultados['falhas'] += 1
            resultados['detalhes'].append("❌ create_fretes_agent não tem agent_type")
            logger.error("❌ create_fretes_agent não tem agent_type")
            
    except Exception as e:
        resultados['testes_executados'] += 1
        resultados['falhas'] += 1
        resultados['detalhes'].append(f"❌ Erro ao testar create_fretes_agent: {e}")
        logger.error(f"❌ Erro ao testar create_fretes_agent: {e}")
    
    return resultados

def main():
    """Função principal"""
    print("🔍 DIAGNÓSTICO - Problema com agent_type")
    print("=" * 50)
    
    resultados = testar_agent_type_issue()
    
    print("\n📊 RESULTADOS:")
    print(f"Testes executados: {resultados['testes_executados']}")
    print(f"Sucessos: {resultados['sucessos']}")
    print(f"Falhas: {resultados['falhas']}")
    print(f"Taxa de sucesso: {(resultados['sucessos'] / resultados['testes_executados'] * 100):.1f}%")
    
    print("\n📋 DETALHES:")
    for detalhe in resultados['detalhes']:
        print(f"  {detalhe}")
    
    if resultados['falhas'] > 0:
        print(f"\n🚨 PROBLEMAS ENCONTRADOS: {resultados['falhas']}")
        return 1
    else:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        return 0

if __name__ == "__main__":
    exit(main()) 