#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO COMPLETO DA INTEGRAÇÃO CLAUDE AI
==============================================

Testa toda a cadeia de integração entre sistema antigo e novo.
"""

import sys
import os
import traceback
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def teste_sistema_antigo():
    """Testa se o sistema antigo funciona corretamente"""
    try:
        print("🔧 Testando sistema antigo...")
        from app.claude_ai.claude_real_integration import processar_com_claude_real
        
        # Teste básico
        resultado = processar_com_claude_real("Teste básico", {"user_id": "test"})
        print(f"✅ Sistema antigo funcional: {len(resultado)} caracteres")
        
        return True
        
    except Exception as e:
        print(f"❌ Sistema antigo falhou: {e}")
        traceback.print_exc()
        return False

def teste_sistema_novo():
    """Testa se o sistema novo funciona corretamente"""
    try:
        print("🚀 Testando sistema novo...")
        from app.claude_ai_novo.integration.external_api_integration import get_claude_integration
        
        # Obter integração
        integration = get_claude_integration()
        print(f"✅ Integração obtida: {type(integration)}")
        
        # Testar status
        status = integration.get_system_status()
        print(f"✅ Status do sistema: {status.get('system_ready', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sistema novo falhou: {e}")
        traceback.print_exc()
        return False

def teste_interface_transicao():
    """Testa a interface de transição"""
    try:
        print("🔄 Testando interface de transição...")
        from app.claude_transition import get_claude_transition, processar_consulta_transicao
        
        # Obter interface
        transition = get_claude_transition()
        print(f"✅ Interface obtida: {transition.sistema_ativo}")
        
        # Testar consulta
        resultado = processar_consulta_transicao("Teste de transição", {"user_id": "test"})
        print(f"✅ Consulta processada: {len(resultado)} caracteres")
        
        return True
        
    except Exception as e:
        print(f"❌ Interface de transição falhou: {e}")
        traceback.print_exc()
        return False

def teste_learning_core():
    """Testa se o learning core funciona"""
    try:
        print("🧠 Testando learning core...")
        from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
        
        # Obter learning core
        learning = get_lifelong_learning()
        print(f"✅ Learning core obtido: {type(learning)}")
        
        # Testar aplicação de conhecimento
        conhecimento = learning.aplicar_conhecimento("Teste de conhecimento")
        print(f"✅ Conhecimento aplicado: {conhecimento.get('confianca_geral', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Learning core falhou: {e}")
        traceback.print_exc()
        return False

def teste_orchestrators():
    """Testa se os orchestrators funcionam"""
    try:
        print("🎼 Testando orchestrators...")
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        
        # Obter orchestrator
        orchestrator = get_orchestrator_manager()
        print(f"✅ Orchestrator obtido: {type(orchestrator)}")
        
        # Testar status
        status = orchestrator.get_system_status()
        print(f"✅ Status orchestrator: {status.get('total_orchestrators', 0)} orchestrators")
        
        return True
        
    except Exception as e:
        print(f"❌ Orchestrators falharam: {e}")
        traceback.print_exc()
        return False

def teste_rotas_producao():
    """Testa se as rotas de produção funcionam"""
    try:
        print("🌐 Testando rotas de produção...")
        
        # Simular requisição
        from app.claude_transition import processar_consulta_transicao
        resultado = processar_consulta_transicao("Como estão as entregas?", {
            "user_id": 1,
            "username": "teste",
            "perfil": "admin"
        })
        
        print(f"✅ Rota de produção funcional: {len(resultado)} caracteres")
        
        # Verificar se não tem erro específico
        if "No module named 'app.claude_ai_novo.intelligence'" in resultado:
            print("❌ ERRO ESPECÍFICO DETECTADO: Módulo intelligence não encontrado")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Rotas de produção falharam: {e}")
        traceback.print_exc()
        return False

def main():
    """Executa diagnóstico completo"""
    print("🔍 DIAGNÓSTICO COMPLETO DA INTEGRAÇÃO CLAUDE AI")
    print("=" * 60)
    print(f"⏰ Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    testes = [
        ("Sistema Antigo", teste_sistema_antigo),
        ("Sistema Novo", teste_sistema_novo),
        ("Interface Transição", teste_interface_transicao),
        ("Learning Core", teste_learning_core),
        ("Orchestrators", teste_orchestrators),
        ("Rotas Produção", teste_rotas_producao)
    ]
    
    resultados = []
    for nome, teste_func in testes:
        print(f"\n📋 TESTE: {nome}")
        print("-" * 30)
        
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
            status = "✅ SUCESSO" if resultado else "❌ FALHA"
            print(f"🎯 {status}")
            
        except Exception as e:
            print(f"❌ ERRO CRÍTICO: {e}")
            resultados.append((nome, False))
    
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL:")
    print("=" * 60)
    
    sucessos = 0
    for nome, resultado in resultados:
        status = "✅ SUCESSO" if resultado else "❌ FALHA"
        print(f"  {status}: {nome}")
        if resultado:
            sucessos += 1
    
    taxa_sucesso = sucessos / len(resultados) * 100
    print(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{len(resultados)} ({taxa_sucesso:.1f}%)")
    
    if taxa_sucesso == 100:
        print("🎉 TODOS OS TESTES PASSARAM - SISTEMA TOTALMENTE FUNCIONAL!")
        print("✅ PROBLEMA DOS LOGS RESOLVIDO")
    elif taxa_sucesso >= 80:
        print("✅ SISTEMA MAJORITARIAMENTE FUNCIONAL")
        print("⚠️ ALGUMAS MELHORIAS NECESSÁRIAS")
    else:
        print("❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        print("🔧 CORREÇÕES NECESSÁRIAS")
    
    print(f"\n⏰ Concluído em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    return taxa_sucesso == 100

if __name__ == "__main__":
    main() 