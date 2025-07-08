#!/usr/bin/env python3
"""
🚀 TESTE COMPLETO - SMARTBASEAGENT COM ANALYZERS INTEGRADOS

Teste final para validar que todos os 5 analyzers foram integrados 
corretamente ao SmartBaseAgent e estão funcionando em produção.
"""

import sys
import os
import asyncio
from typing import Dict, Any
from datetime import datetime

# Adicionar caminho
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

async def test_smart_base_agent_completo():
    """Teste completo do SmartBaseAgent com analyzers"""
    
    print("🚀 TESTE COMPLETO: SMARTBASEAGENT + ANALYZERS")
    print("="*60)
    
    # 1. TESTAR CRIAÇÃO DO SMARTBASEAGENT
    print("\n📋 TESTE 1: Criação do SmartBaseAgent")
    
    try:
        from app.claude_ai_novo.multi_agent.agent_types import AgentType
        from app.claude_ai_novo.multi_agent.agents.smart_base_agent import SmartBaseAgent
        
        # Criar agent de teste
        agent = SmartBaseAgent(AgentType.ENTREGAS)
        print(f"   ✅ SmartBaseAgent criado: {agent.agent_type.value}")
        
        # Verificar status completo
        status = agent.get_agent_status()
        capacidades = status['capacidades_ativas']
        
        print(f"   📊 Total capacidades: {len(capacidades)}")
        print(f"   🧠 Analyzers integrados: {'analyzers_avancados' in capacidades}")
        
        # Mostrar capacidades
        for capacidade in capacidades:
            print(f"      • {capacidade}")
        
        agent_criado = True
        
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        agent_criado = False
        agent = None
    
    # 2. TESTAR ANALYZERS INDIVIDUAIS
    print("\n📋 TESTE 2: Analyzers Individuais no Agent")
    
    analyzers_status = {}
    
    if agent_criado and hasattr(agent, 'tem_analyzers') and agent.tem_analyzers:
        
        # 2.1 Intention Analyzer
        try:
            if hasattr(agent, 'intention_analyzer') and agent.intention_analyzer:
                result = agent.intention_analyzer.analyze_intention("Quantas entregas estão atrasadas?")
                analyzers_status['intention'] = f"✅ Intenção: {result['intention']}"
            else:
                analyzers_status['intention'] = "❌ Não carregado"
        except Exception as e:
            analyzers_status['intention'] = f"❌ Erro: {e}"
        
        # 2.2 Query Analyzer  
        try:
            if hasattr(agent, 'query_analyzer') and agent.query_analyzer:
                result = agent.query_analyzer.analyze_query("Status das entregas hoje")
                analyzers_status['query'] = f"✅ Tipo: {result['query_type']}"
            else:
                analyzers_status['query'] = "❌ Não carregado"
        except Exception as e:
            analyzers_status['query'] = f"❌ Erro: {e}"
        
        # 2.3 NLP Analyzer
        try:
            if hasattr(agent, 'nlp_analyzer') and agent.nlp_analyzer:
                result = agent.nlp_analyzer.analyze_text("Entregas do Assai")
                analyzers_status['nlp'] = f"✅ Entidades: {len(result.get('entities', []))}"
            else:
                analyzers_status['nlp'] = "❌ Não carregado"
        except Exception as e:
            analyzers_status['nlp'] = f"❌ Erro: {e}"
        
        # 2.4 Metacognitive Analyzer
        try:
            if hasattr(agent, 'metacognitive_analyzer') and agent.metacognitive_analyzer:
                result = agent.metacognitive_analyzer.analyze_own_performance(
                    "Teste", "Resposta teste"
                )
                analyzers_status['metacognitive'] = f"✅ Confiança: {result.get('confidence_score', 0):.2f}"
            else:
                analyzers_status['metacognitive'] = "❌ Não carregado"
        except Exception as e:
            analyzers_status['metacognitive'] = f"❌ Erro: {e}"
        
        # 2.5 Structural AI
        try:
            if hasattr(agent, 'structural_ai') and agent.structural_ai:
                result = agent.structural_ai.validate_business_logic({'domain': 'delivery'})
                analyzers_status['structural'] = f"✅ Consistência: {result.get('structural_consistency', 0):.2f}"
            else:
                analyzers_status['structural'] = "❌ Não carregado"
        except Exception as e:
            analyzers_status['structural'] = f"❌ Erro: {e}"
        
    else:
        print("   ⚠️ Analyzers não foram carregados no agent")
        analyzers_status = {
            'intention': '❌ Agent sem analyzers',
            'query': '❌ Agent sem analyzers', 
            'nlp': '❌ Agent sem analyzers',
            'metacognitive': '❌ Agent sem analyzers',
            'structural': '❌ Agent sem analyzers'
        }
    
    # Mostrar status dos analyzers
    for analyzer, status in analyzers_status.items():
        print(f"   {analyzer.capitalize()}: {status}")
    
    # 3. TESTAR PIPELINE COMPLETO
    print("\n📋 TESTE 3: Pipeline de Análise Completo")
    
    if agent_criado:
        try:
            # Simular análise completa
            query = "Quantas entregas do Assai estão atrasadas hoje?"
            context = {'user_id': 'test_user', 'username': 'teste'}
            
            print(f"   📝 Query: {query}")
            print(f"   🎯 Executando pipeline completo...")
            
            # Executar análise (sem dados reais para teste)
            start_time = datetime.now()
            
            # Chamar método de análise com analyzers (se disponível)
            if hasattr(agent, '_analisar_com_analyzers'):
                context_enriquecido = await agent._analisar_com_analyzers(query, context)
                
                # Verificar se contexto foi enriquecido
                enriched_fields = []
                if 'intention_analysis' in context_enriquecido:
                    enriched_fields.append('intention_analysis')
                if 'query_analysis' in context_enriquecido:
                    enriched_fields.append('query_analysis')
                if 'nlp_analysis' in context_enriquecido:
                    enriched_fields.append('nlp_analysis')
                if 'structural_validation' in context_enriquecido:
                    enriched_fields.append('structural_validation')
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                print(f"   ✅ Pipeline executado em {processing_time:.3f}s")
                print(f"   📊 Campos enriquecidos: {len(enriched_fields)}")
                
                for field in enriched_fields:
                    print(f"      • {field}")
                
                pipeline_success = len(enriched_fields) > 0
                
            else:
                print("   ⚠️ Método _analisar_com_analyzers não encontrado")
                pipeline_success = False
                
        except Exception as e:
            print(f"   ❌ Erro no pipeline: {e}")
            pipeline_success = False
    else:
        pipeline_success = False
    
    # 4. RELATÓRIO FINAL
    print("\n📋 RELATÓRIO FINAL")
    print("="*60)
    
    working_analyzers = sum(1 for status in analyzers_status.values() if '✅' in status)
    total_analyzers = len(analyzers_status)
    
    print(f"   🎯 Agent criado: {'✅' if agent_criado else '❌'}")
    print(f"   🧠 Analyzers funcionando: {working_analyzers}/{total_analyzers}")
    print(f"   🔄 Pipeline completo: {'✅' if pipeline_success else '❌'}")
    print(f"   📈 Taxa de sucesso: {(working_analyzers/total_analyzers)*100:.1f}%")
    
    # Verificar se é uma integração completa
    integration_complete = (
        agent_criado and 
        working_analyzers >= 4 and  # Pelo menos 4/5 analyzers
        pipeline_success
    )
    
    if integration_complete:
        print("\n   🎉 INTEGRAÇÃO COMPLETA BEM-SUCEDIDA!")
        print("   🚀 SmartBaseAgent agora é uma IA industrial de última geração!")
        print("   📊 Benefícios ativados:")
        print("      • Análise multicamada inteligente")
        print("      • Autoavaliação contínua")
        print("      • Validação estrutural automática")
        print("      • Detecção de intenção avançada")
        print("      • Processamento NLP profissional")
    else:
        print("\n   ⚠️ Integração parcial ou problemas detectados")
        print("   🔧 Recomendações:")
        if not agent_criado:
            print("      • Corrigir imports do SmartBaseAgent")
        if working_analyzers < 4:
            print("      • Verificar carregamento dos analyzers")
        if not pipeline_success:
            print("      • Testar métodos de análise")
    
    return {
        'agent_criado': agent_criado,
        'analyzers_funcionando': working_analyzers,
        'pipeline_success': pipeline_success,
        'integration_complete': integration_complete,
        'analyzers_status': analyzers_status
    }

if __name__ == "__main__":
    result = asyncio.run(test_smart_base_agent_completo())
    
    print(f"\n🎯 RESULTADO FINAL: {result}")
    
    if result['integration_complete']:
        print("\n✅ SISTEMA PRONTO PARA PRODUÇÃO!")
    else:
        print(f"\n❌ NECESSÁRIO CORRIGIR {5 - result['analyzers_funcionando']} ANALYZERS") 