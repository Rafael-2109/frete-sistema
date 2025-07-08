#!/usr/bin/env python3
"""
🧪 TESTE DE OTIMIZAÇÃO DO CONHECIMENTO
Valida se a remoção da duplicação funcionou e se os agentes mantêm conhecimento específico
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.claude_ai_novo.multi_agent.agents.smart_base_agent import SmartBaseAgent
from app.claude_ai_novo.multi_agent.agents.entregas_agent import EntregasAgent
from app.claude_ai_novo.multi_agent.agents.pedidos_agent import PedidosAgent
from app.claude_ai_novo.multi_agent.agents.fretes_agent import FreteAgent
from app.claude_ai_novo.multi_agent.agents.financeiro_agent import FinanceiroAgent
from app.claude_ai_novo.multi_agent.agent_types import AgentType

def teste_conhecimento_otimizado():
    """Testa se a otimização do conhecimento funcionou corretamente"""
    
    print("🧪 TESTE DE OTIMIZAÇÃO DO CONHECIMENTO")
    print("=" * 50)
    
    resultados = []
    
    # 1. TESTE SmartBaseAgent (deve ter conhecimento genérico básico)
    print("\n1. 📊 TESTANDO SmartBaseAgent (genérico):")
    try:
        smart_agent = SmartBaseAgent(AgentType.ENTREGAS)
        conhecimento_smart = smart_agent._load_domain_knowledge()
        keywords_smart = smart_agent._get_domain_keywords()
        
        print(f"   ✅ Conhecimento genérico: {conhecimento_smart}")
        print(f"   ✅ Keywords genéricas: {keywords_smart}")
        
        # Verificar se não tem conhecimento específico duplicado
        if 'modelos_principais' not in conhecimento_smart:
            print("   ✅ SUCESSO: Conhecimento específico removido")
            resultados.append("✅ SmartBaseAgent otimizado")
        else:
            print("   ❌ FALHA: Ainda tem conhecimento específico duplicado")
            resultados.append("❌ SmartBaseAgent não otimizado")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ SmartBaseAgent com erro")
    
    # 2. TESTE EntregasAgent (deve ter conhecimento específico)
    print("\n2. 🚚 TESTANDO EntregasAgent (específico):")
    try:
        entregas_agent = EntregasAgent()
        conhecimento_entregas = entregas_agent._load_domain_knowledge()
        keywords_entregas = entregas_agent._get_domain_keywords()
        
        print(f"   ✅ Conhecimento específico: {len(str(conhecimento_entregas))} chars")
        print(f"   ✅ Keywords específicas: {len(keywords_entregas)} palavras")
        
        # Verificar se tem conhecimento específico
        if 'main_models' in conhecimento_entregas and 'EntregaMonitorada' in str(conhecimento_entregas):
            print("   ✅ SUCESSO: Conhecimento específico de entregas mantido")
            resultados.append("✅ EntregasAgent específico")
        else:
            print("   ❌ FALHA: Conhecimento específico não encontrado")
            resultados.append("❌ EntregasAgent sem conhecimento específico")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ EntregasAgent com erro")
    
    # 3. TESTE PedidosAgent (deve ter conhecimento específico)
    print("\n3. 📦 TESTANDO PedidosAgent (específico):")
    try:
        pedidos_agent = PedidosAgent()
        conhecimento_pedidos = pedidos_agent._load_domain_knowledge()
        keywords_pedidos = pedidos_agent._get_domain_keywords()
        
        print(f"   ✅ Conhecimento específico: {len(str(conhecimento_pedidos))} chars")
        print(f"   ✅ Keywords específicas: {len(keywords_pedidos)} palavras")
        
        # Verificar se tem conhecimento específico
        if 'main_models' in conhecimento_pedidos and 'Pedido' in str(conhecimento_pedidos):
            print("   ✅ SUCESSO: Conhecimento específico de pedidos mantido")
            resultados.append("✅ PedidosAgent específico")
        else:
            print("   ❌ FALHA: Conhecimento específico não encontrado")
            resultados.append("❌ PedidosAgent sem conhecimento específico")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ PedidosAgent com erro")
    
    # 4. TESTE FreteAgent (deve ter conhecimento específico)
    print("\n4. 🚛 TESTANDO FreteAgent (específico):")
    try:
        frete_agent = FreteAgent()
        conhecimento_frete = frete_agent._load_domain_knowledge()
        keywords_frete = frete_agent._get_domain_keywords()
        
        print(f"   ✅ Conhecimento específico: {len(str(conhecimento_frete))} chars")
        print(f"   ✅ Keywords específicas: {len(keywords_frete)} palavras")
        
        # Verificar se tem conhecimento específico
        if 'main_models' in conhecimento_frete and 'Frete' in str(conhecimento_frete):
            print("   ✅ SUCESSO: Conhecimento específico de fretes mantido")
            resultados.append("✅ FreteAgent específico")
        else:
            print("   ❌ FALHA: Conhecimento específico não encontrado")
            resultados.append("❌ FreteAgent sem conhecimento específico")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ FreteAgent com erro")
    
    # 5. TESTE FinanceiroAgent (deve ter conhecimento específico)
    print("\n5. 💰 TESTANDO FinanceiroAgent (específico):")
    try:
        financeiro_agent = FinanceiroAgent()
        conhecimento_financeiro = financeiro_agent._load_domain_knowledge()
        keywords_financeiro = financeiro_agent._get_domain_keywords()
        
        print(f"   ✅ Conhecimento específico: {len(str(conhecimento_financeiro))} chars")
        print(f"   ✅ Keywords específicas: {len(keywords_financeiro)} palavras")
        
        # Verificar se tem conhecimento específico
        if 'main_models' in conhecimento_financeiro and 'RelatorioFaturamentoImportado' in str(conhecimento_financeiro):
            print("   ✅ SUCESSO: Conhecimento específico financeiro mantido")
            resultados.append("✅ FinanceiroAgent específico")
        else:
            print("   ❌ FALHA: Conhecimento específico não encontrado")
            resultados.append("❌ FinanceiroAgent sem conhecimento específico")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append("❌ FinanceiroAgent com erro")
    
    # 📊 RESUMO DOS RESULTADOS
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS RESULTADOS:")
    print("=" * 50)
    
    sucessos = len([r for r in resultados if r.startswith("✅")])
    total = len(resultados)
    
    for resultado in resultados:
        print(f"   {resultado}")
    
    print(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
    
    if sucessos == total:
        print("🎉 OTIMIZAÇÃO PERFEITA! Duplicação removida e conhecimento específico mantido")
        return True
    else:
        print("⚠️ OTIMIZAÇÃO PARCIAL: Alguns problemas detectados")
        return False

if __name__ == "__main__":
    teste_conhecimento_otimizado() 