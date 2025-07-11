#!/usr/bin/env python3
"""
🧪 TESTE PÓS-REMOÇÃO DOS ADAPTERS
Verificar se o sistema funciona sem os adapters
"""

import sys
import os
import traceback
from datetime import datetime

def teste_imports_diretos():
    """Testa se os imports diretos funcionam"""
    
    resultados = {
        'get_sistema_real_data': {'status': 'error', 'detalhes': ''},
        'get_conversation_context': {'status': 'error', 'detalhes': ''},
        'get_db_session': {'status': 'error', 'detalhes': ''}
    }
    
    # Teste 1: get_sistema_real_data
    try:
        from data.providers.data_provider import get_sistema_real_data
        sistema = get_sistema_real_data()
        resultados['get_sistema_real_data'] = {
            'status': 'success',
            'detalhes': f'Sistema inicializado: {type(sistema).__name__}'
        }
        print("✅ get_sistema_real_data: OK")
    except Exception as e:
        resultados['get_sistema_real_data'] = {
            'status': 'error', 
            'detalhes': f'Erro: {e}'
        }
        print(f"❌ get_sistema_real_data: {e}")
    
    # Teste 2: get_conversation_context
    try:
        from intelligence.conversation.conversation_context import get_conversation_context
        context = get_conversation_context()
        resultados['get_conversation_context'] = {
            'status': 'success',
            'detalhes': f'Contexto: {type(context).__name__ if context else "None"}'
        }
        print("✅ get_conversation_context: OK")
    except Exception as e:
        resultados['get_conversation_context'] = {
            'status': 'error',
            'detalhes': f'Erro: {e}'
        }
        print(f"❌ get_conversation_context: {e}")
    
    # Teste 3: get_db_session (sistema antigo)
    try:
        sys.path.append('../../claude_ai')
        from lifelong_learning import _get_db_session
        session = _get_db_session()
        resultados['get_db_session'] = {
            'status': 'success',
            'detalhes': f'Session: {type(session).__name__ if session else "None"}'
        }
        print("✅ get_db_session: OK")
    except Exception as e:
        resultados['get_db_session'] = {
            'status': 'error',
            'detalhes': f'Erro: {e}'
        }
        print(f"❌ get_db_session: {e}")
    
    return resultados

def teste_advanced_integration():
    """Testa se o advanced_integration funciona sem adapters"""
    
    try:
        from integration.advanced.advanced_integration import AdvancedAIIntegration
        
        # Tentar inicializar
        ai = AdvancedAIIntegration()
        
        print("✅ AdvancedAIIntegration: Inicializado com sucesso")
        
        # Verificar se os componentes estão funcionando
        componentes = {
            'sistema_real': ai.sistema_real,
            'conversation_context': ai.conversation_context,
            'multi_agent': ai.multi_agent,
            'human_learning': ai.human_learning,
            'metacognitive': ai.metacognitive,
            'structural_ai': ai.structural_ai,
            'semantic_loop': ai.semantic_loop
        }
        
        componentes_ok = 0
        for nome, componente in componentes.items():
            if componente is not None:
                componentes_ok += 1
                print(f"  ✅ {nome}: {type(componente).__name__}")
            else:
                print(f"  ❌ {nome}: None")
        
        return {
            'status': 'success',
            'componentes_ok': componentes_ok,
            'total_componentes': len(componentes),
            'detalhes': f'{componentes_ok}/{len(componentes)} componentes funcionando'
        }
        
    except Exception as e:
        print(f"❌ AdvancedAIIntegration: {e}")
        traceback.print_exc()
        return {
            'status': 'error',
            'detalhes': f'Erro: {e}'
        }

def main():
    """Função principal"""
    
    print("🧪 TESTE PÓS-REMOÇÃO DOS ADAPTERS")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Teste 1: Imports diretos
    print("📋 TESTE 1: Imports Diretos")
    print("-" * 30)
    resultados_imports = teste_imports_diretos()
    
    # Teste 2: AdvancedAIIntegration
    print()
    print("📋 TESTE 2: AdvancedAIIntegration")
    print("-" * 30)
    resultado_integration = teste_advanced_integration()
    
    # Resumo final
    print()
    print("📊 RESUMO FINAL")
    print("=" * 50)
    
    # Contabilizar sucessos
    imports_sucessos = sum(1 for r in resultados_imports.values() if r['status'] == 'success')
    total_imports = len(resultados_imports)
    
    integration_sucesso = 1 if resultado_integration['status'] == 'success' else 0
    
    total_sucessos = imports_sucessos + integration_sucesso
    total_testes = total_imports + 1
    
    print(f"✅ Imports diretos: {imports_sucessos}/{total_imports}")
    print(f"✅ AdvancedAIIntegration: {integration_sucesso}/1")
    print(f"🎯 Taxa de sucesso: {total_sucessos}/{total_testes} ({total_sucessos/total_testes*100:.1f}%)")
    
    # Veredicto
    if total_sucessos == total_testes:
        print()
        print("🎉 VEREDICTO: REMOÇÃO DOS ADAPTERS FOI SUCESSO!")
        print("✅ Sistema funciona 100% sem adapters")
        print("✅ Imports diretos funcionando")
        print("✅ Complexidade reduzida")
    elif total_sucessos >= total_testes * 0.8:
        print()
        print("⚠️ VEREDICTO: REMOÇÃO PARCIALMENTE SUCESSO")
        print("⚠️ Alguns componentes podem ter problemas")
        print("⚠️ Verificar detalhes dos erros")
    else:
        print()
        print("❌ VEREDICTO: REMOÇÃO CAUSOU PROBLEMAS")
        print("❌ Muitos componentes não funcionam")
        print("❌ Considerar reverter ou corrigir")
    
    # Salvar relatório
    relatorio = {
        'timestamp': datetime.now().isoformat(),
        'teste': 'pos_remocao_adapters',
        'resultados_imports': resultados_imports,
        'resultado_integration': resultado_integration,
        'estatisticas': {
            'imports_sucessos': imports_sucessos,
            'total_imports': total_imports,
            'integration_sucesso': integration_sucesso,
            'total_sucessos': total_sucessos,
            'total_testes': total_testes,
            'taxa_sucesso': total_sucessos/total_testes
        }
    }
    
    try:
        import json
        with open('TESTE_POS_REMOCAO_ADAPTERS.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Relatório salvo: TESTE_POS_REMOCAO_ADAPTERS.json")
    except Exception as e:
        print(f"⚠️ Erro ao salvar relatório: {e}")

if __name__ == "__main__":
    main() 