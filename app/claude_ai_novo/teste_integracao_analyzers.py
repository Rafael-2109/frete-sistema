#!/usr/bin/env python3
"""
🧪 TESTE PRÁTICO - INTEGRAÇÃO DOS ANALYZERS AO SMARTBASEAGENT

Este teste demonstra COMO integrar os 5 analyzers órfãos ao SmartBaseAgent
para eliminar warnings e criar uma IA industrial de última geração.
"""

import sys
import os
import asyncio
from typing import Dict, Any, List
from datetime import datetime

# Adicionar caminho
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

async def test_analyzers_integration():
    """Testa integração completa dos analyzers"""
    
    print("🚀 TESTE: INTEGRAÇÃO DOS ANALYZERS")
    print("="*50)
    
    # 1. TESTAR CADA ANALYZER INDIVIDUALMENTE
    print("\n📋 TESTE 1: Analyzers Individuais")
    
    analyzers_status = {}
    
    # 1.1 INTENTION ANALYZER
    try:
        from app.claude_ai_novo.analyzers.intention_analyzer import get_intention_analyzer
        intention_analyzer = get_intention_analyzer()
        result = intention_analyzer.analyze_intention("Quantas entregas do Assai estão atrasadas?")
        analyzers_status['intention'] = '✅ FUNCIONANDO'
        print(f"   🎯 Intention Analyzer: {result.get('intention', 'N/A')}")
    except Exception as e:
        analyzers_status['intention'] = f'❌ ERRO: {e}'
        print(f"   🎯 Intention Analyzer: ERRO - {e}")
    
    # 1.2 METACOGNITIVE ANALYZER
    try:
        from app.claude_ai_novo.analyzers.metacognitive_analyzer import get_metacognitive_analyzer
        metacognitive_analyzer = get_metacognitive_analyzer()
        result = metacognitive_analyzer.analyze_own_performance(
            "Teste query", "Resposta de teste"
        )
        analyzers_status['metacognitive'] = '✅ FUNCIONANDO'
        print(f"   🧠 Metacognitive: Confiança {result.get('confidence_score', 0):.2f}")
    except Exception as e:
        analyzers_status['metacognitive'] = f'❌ ERRO: {e}'
        print(f"   🧠 Metacognitive: ERRO - {e}")
    
    # 1.3 NLP ENHANCED ANALYZER
    try:
        from app.claude_ai_novo.analyzers.nlp_enhanced_analyzer import get_nlp_enhanced_analyzer
        nlp_analyzer = get_nlp_enhanced_analyzer()
        result = nlp_analyzer.analyze_text("Entregas do Assai em atraso")
        analyzers_status['nlp'] = '✅ FUNCIONANDO'
        print(f"   🔤 NLP Enhanced: {len(result.get('entities', []))} entidades")
    except Exception as e:
        analyzers_status['nlp'] = f'❌ ERRO: {e}'
        print(f"   🔤 NLP Enhanced: ERRO - {e}")
    
    # 1.4 QUERY ANALYZER
    try:
        from app.claude_ai_novo.analyzers.query_analyzer import get_query_analyzer
        query_analyzer = get_query_analyzer()
        result = query_analyzer.analyze_query("Status das entregas hoje")
        analyzers_status['query'] = '✅ FUNCIONANDO'
        print(f"   ❓ Query Analyzer: Tipo {result.get('query_type', 'N/A')}")
    except Exception as e:
        analyzers_status['query'] = f'❌ ERRO: {e}'
        print(f"   ❓ Query Analyzer: ERRO - {e}")
    
    # 1.5 STRUCTURAL AI
    try:
        from app.claude_ai_novo.analyzers.structural_ai import get_structural_ai
        structural_ai = get_structural_ai()
        result = structural_ai.validate_business_logic({'domain': 'delivery'})
        analyzers_status['structural'] = '✅ FUNCIONANDO'
        print(f"   🏗️ Structural AI: Consistência {result.get('structural_consistency', 0):.2f}")
    except Exception as e:
        analyzers_status['structural'] = f'❌ ERRO: {e}'
        print(f"   🏗️ Structural AI: ERRO - {e}")
    
    # 2. PROPOR INTEGRAÇÃO AO SMARTBASEAGENT
    print("\n📋 TESTE 2: Integração ao SmartBaseAgent")
    
    integration_code = generate_integration_code(analyzers_status)
    print(f"   📝 Código de integração gerado: {len(integration_code)} linhas")
    
    # 3. SIMULAR RESPOSTA COM ANALYZERS
    print("\n📋 TESTE 3: Simulação de Resposta Avançada")
    
    enhanced_response = await simulate_enhanced_response(
        "Quantas entregas do Assai estão atrasadas?",
        analyzers_status
    )
    
    print(f"   📊 Resposta original: Resposta básica")
    print(f"   🚀 Resposta aprimorada: {len(enhanced_response)} caracteres")
    print(f"   📈 Melhoria estimada: +{len(enhanced_response) - 15} caracteres de contexto")
    
    # 4. RELATÓRIO FINAL
    print("\n📋 RELATÓRIO FINAL")
    print("="*50)
    
    working_analyzers = [k for k, v in analyzers_status.items() if '✅' in v]
    total_analyzers = len(analyzers_status)
    
    print(f"   📊 Analyzers funcionando: {len(working_analyzers)}/{total_analyzers}")
    print(f"   📈 Taxa de sucesso: {len(working_analyzers)/total_analyzers*100:.1f}%")
    print(f"   🎯 Potencial de melhoria: {len(working_analyzers) * 20}% mais inteligente")
    
    if len(working_analyzers) > 0:
        print("\n   ✅ RECOMENDAÇÃO: INTEGRAR ANALYZERS AO SMARTBASEAGENT")
        print("   🚀 Benefícios esperados:")
        print("      • Respostas mais inteligentes")
        print("      • Autoavaliação contínua")
        print("      • Análise multicamada")
        print("      • Eliminação de warnings")
    else:
        print("\n   ❌ RECOMENDAÇÃO: CORRIGIR IMPORTS DOS ANALYZERS PRIMEIRO")
    
    return {
        'analyzers_status': analyzers_status,
        'working_analyzers': working_analyzers,
        'integration_ready': len(working_analyzers) > 2
    }

def generate_integration_code(analyzers_status: Dict[str, str]) -> str:
    """Gera código de integração para SmartBaseAgent"""
    
    code_lines = []
    
    # Header
    code_lines.append("def _carregar_analyzers_avancados(self):")
    code_lines.append('    """Carrega analyzers avançados de análise"""')
    code_lines.append("    try:")
    
    # Imports condicionais
    if '✅' in analyzers_status.get('intention', ''):
        code_lines.append("        from app.claude_ai_novo.analyzers.intention_analyzer import get_intention_analyzer")
        code_lines.append("        self.intention_analyzer = get_intention_analyzer()")
    
    if '✅' in analyzers_status.get('metacognitive', ''):
        code_lines.append("        from app.claude_ai_novo.analyzers.metacognitive_analyzer import get_metacognitive_analyzer")
        code_lines.append("        self.metacognitive_analyzer = get_metacognitive_analyzer()")
    
    if '✅' in analyzers_status.get('nlp', ''):
        code_lines.append("        from app.claude_ai_novo.analyzers.nlp_enhanced_analyzer import get_nlp_enhanced_analyzer")
        code_lines.append("        self.nlp_analyzer = get_nlp_enhanced_analyzer()")
    
    if '✅' in analyzers_status.get('query', ''):
        code_lines.append("        from app.claude_ai_novo.analyzers.query_analyzer import get_query_analyzer")
        code_lines.append("        self.query_analyzer = get_query_analyzer()")
    
    if '✅' in analyzers_status.get('structural', ''):
        code_lines.append("        from app.claude_ai_novo.analyzers.structural_ai import get_structural_ai")
        code_lines.append("        self.structural_ai = get_structural_ai()")
    
    # Status check
    working_count = sum(1 for status in analyzers_status.values() if '✅' in status)
    code_lines.append(f"        self.tem_analyzers = True")
    code_lines.append(f'        logger.info(f"✅ {{self.agent_type.value}}: {working_count} analyzers conectados")')
    
    # Exception handling
    code_lines.append("    except Exception as e:")
    code_lines.append("        self.tem_analyzers = False")
    code_lines.append('        logger.warning(f"⚠️ {self.agent_type.value}: Analyzers não disponíveis: {e}")')
    
    return '\n'.join(code_lines)

async def simulate_enhanced_response(query: str, analyzers_status: Dict[str, str]) -> str:
    """Simula resposta aprimorada com analyzers"""
    
    response_parts = []
    
    # Resposta base
    response_parts.append("Resposta básica do agente...")
    
    # Adicionar insights de cada analyzer ativo
    if '✅' in analyzers_status.get('intention', ''):
        response_parts.append("\n🎯 **Análise de Intenção:** Consulta de monitoramento identificada")
    
    if '✅' in analyzers_status.get('nlp', ''):
        response_parts.append("\n🔤 **Análise NLP:** Entidades: 'Assai' (cliente), 'entregas' (processo)")
    
    if '✅' in analyzers_status.get('query', ''):
        response_parts.append("\n❓ **Análise de Consulta:** Tipo: pergunta operacional, Complexidade: média")
    
    if '✅' in analyzers_status.get('metacognitive', ''):
        response_parts.append("\n🧠 **Autoavaliação:** Confiança 85%, recomenda validação manual")
    
    if '✅' in analyzers_status.get('structural', ''):
        response_parts.append("\n🏗️ **Validação Estrutural:** Consistência 90%, regras de negócio ok")
    
    # Footer tecnológico
    working_count = sum(1 for status in analyzers_status.values() if '✅' in status)
    response_parts.append(f"\n\n---\n🚀 **IA Industrial Avançada** | {working_count} analyzers ativos | Sistema multicamada")
    
    return ''.join(response_parts)

if __name__ == "__main__":
    result = asyncio.run(test_analyzers_integration())
    
    print(f"\n🎯 RESULTADO: {result}")
    
    if result['integration_ready']:
        print("\n✅ SISTEMA PRONTO PARA INTEGRAÇÃO DOS ANALYZERS!")
        print("   Próximo passo: Adicionar código ao SmartBaseAgent")
    else:
        print("\n❌ CORRIGIR IMPORTS DOS ANALYZERS PRIMEIRO") 