#!/usr/bin/env python3
"""
🧪 TESTE RÁPIDO AGENTES - Verificação de Imports e Inicialização

Teste simples para verificar se os problemas de import foram corrigidos.
"""

import sys
import os
from datetime import datetime

# Adicionar caminho para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def testar_imports():
    """Testa se todos os agentes podem ser importados"""
    print("🧪 TESTE RÁPIDO - IMPORTS DOS AGENTES")
    print("=" * 50)
    
    agentes_para_testar = [
        ('SmartBaseAgent', 'multi_agent.agents.smart_base_agent'),
        ('EntregasAgent', 'multi_agent.agents.entregas_agent'),
        ('EmbarquesAgent', 'multi_agent.agents.embarques_agent'),
        ('FinanceiroAgent', 'multi_agent.agents.financeiro_agent'),
        ('PedidosAgent', 'multi_agent.agents.pedidos_agent'),
        ('FretesAgent', 'multi_agent.agents.fretes_agent')
    ]
    
    sucessos = 0
    falhas = 0
    
    for nome_agente, modulo in agentes_para_testar:
        try:
            # Import dinâmico
            from importlib import import_module
            modulo_importado = import_module(modulo)
            classe_agente = getattr(modulo_importado, nome_agente)
            
            print(f"✅ {nome_agente}: Import OK")
            sucessos += 1
            
            # Teste básico de inicialização (apenas para agentes específicos)
            if nome_agente != 'SmartBaseAgent':
                try:
                    agente = classe_agente()
                    print(f"   └─ Inicialização: ✅ OK")
                    
                    # Verificar se é SmartBaseAgent
                    from multi_agent.agents.smart_base_agent import SmartBaseAgent
                    is_smart = isinstance(agente, SmartBaseAgent)
                    print(f"   └─ SmartBaseAgent: {'✅' if is_smart else '❌'} {is_smart}")
                    
                except Exception as e:
                    print(f"   └─ Inicialização: ❌ {str(e)[:50]}...")
                    
        except Exception as e:
            print(f"❌ {nome_agente}: {str(e)[:60]}...")
            falhas += 1
    
    print(f"\n📊 RESULTADO:")
    print(f"✅ Sucessos: {sucessos}/{len(agentes_para_testar)}")
    print(f"❌ Falhas: {falhas}/{len(agentes_para_testar)}")
    
    if falhas == 0:
        print("🎉 TODOS OS AGENTES FUNCIONANDO!")
        return True
    else:
        print("⚠️ AINDA HÁ PROBLEMAS A CORRIGIR")
        return False

def testar_import_via_init():
    """Testa import via __init__.py"""
    print("\n🔍 TESTE VIA __INIT__.PY")
    print("-" * 30)
    
    try:
        from multi_agent.agents import (
            SmartBaseAgent,
            EntregasAgent,
            EmbarquesAgent,
            FinanceiroAgent,
            PedidosAgent,
            FretesAgent
        )
        print("✅ Import via __init__.py: OK")
        
        # Testar criação de um agente
        agente = EntregasAgent()
        is_smart = isinstance(agente, SmartBaseAgent)
        print(f"✅ EntregasAgent é SmartBaseAgent: {is_smart}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import via __init__.py: {e}")
        return False

def main():
    """Função principal"""
    print(f"🕒 {datetime.now().strftime('%H:%M:%S')} - Iniciando teste rápido...")
    
    # Teste 1: Imports individuais
    test1 = testar_imports()
    
    # Teste 2: Import via __init__.py  
    test2 = testar_import_via_init()
    
    print(f"\n🎯 RESULTADO FINAL:")
    if test1 and test2:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("🚀 Sistema pronto para uso!")
    else:
        print("❌ AINDA HÁ PROBLEMAS")
        print("🔧 Necessário mais correções")

if __name__ == "__main__":
    main() 