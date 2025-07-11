#!/usr/bin/env python3
"""
🔍 TESTE DE INTEGRAÇÃO ENTRE SISTEMA ANTIGO E NOVO
=================================================

Testa se o claude_ai_novo está funcionando corretamente e se pode ser 
importado pelo sistema antigo sem erros.
"""

import sys
import os
import traceback

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def teste_importacao_learning_core():
    """Testa se o learning_core pode ser importado"""
    try:
        print("🧠 Testando importação do learning_core...")
        from app.claude_ai_novo.learners.learning_core import get_lifelong_learning
        
        lifelong = get_lifelong_learning()
        print(f"✅ Learning Core importado com sucesso: {type(lifelong)}")
        
        # Testar método aplicar_conhecimento
        teste_consulta = "Como estão as entregas do Atacadão?"
        resultado = lifelong.aplicar_conhecimento(teste_consulta)
        print(f"✅ Método aplicar_conhecimento funcionou: {type(resultado)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na importação do learning_core: {e}")
        traceback.print_exc()
        return False

def teste_importacao_orchestrators():
    """Testa se os orchestrators podem ser importados"""
    try:
        print("🎼 Testando importação dos orchestrators...")
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        
        orchestrator = get_orchestrator_manager()
        print(f"✅ Orchestrator Manager importado com sucesso: {type(orchestrator)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na importação dos orchestrators: {e}")
        traceback.print_exc()
        return False

def teste_importacao_analyzers():
    """Testa se os analyzers podem ser importados"""
    try:
        print("🔍 Testando importação dos analyzers...")
        from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager
        
        analyzer = get_analyzer_manager()
        print(f"✅ Analyzer Manager importado com sucesso: {type(analyzer)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na importação dos analyzers: {e}")
        traceback.print_exc()
        return False

def teste_importacao_security():
    """Testa se o security guard pode ser importado"""
    try:
        print("🔒 Testando importação do security guard...")
        from app.claude_ai_novo.security.security_guard import get_security_guard
        
        security = get_security_guard()
        print(f"✅ Security Guard importado com sucesso: {type(security)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na importação do security guard: {e}")
        traceback.print_exc()
        return False

def teste_inicializacao_sistema_novo():
    """Testa se o sistema novo pode ser inicializado"""
    try:
        print("🚀 Testando inicialização do sistema novo...")
        from app.claude_ai_novo import get_system_status
        
        status = get_system_status()
        print(f"✅ Sistema novo inicializado: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na inicialização do sistema novo: {e}")
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes"""
    print("🔍 TESTE DE INTEGRAÇÃO SISTEMA ANTIGO → NOVO")
    print("=" * 50)
    
    testes = [
        ("Learning Core", teste_importacao_learning_core),
        ("Orchestrators", teste_importacao_orchestrators),
        ("Analyzers", teste_importacao_analyzers),
        ("Security Guard", teste_importacao_security),
        ("Sistema Novo", teste_inicializacao_sistema_novo)
    ]
    
    resultados = []
    for nome, teste_func in testes:
        print(f"\n📋 Executando teste: {nome}")
        resultado = teste_func()
        resultados.append((nome, resultado))
        print(f"{'✅' if resultado else '❌'} {nome}: {'SUCESSO' if resultado else 'FALHA'}")
    
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES:")
    
    sucessos = 0
    for nome, resultado in resultados:
        status = "✅ SUCESSO" if resultado else "❌ FALHA"
        print(f"  {status}: {nome}")
        if resultado:
            sucessos += 1
    
    print(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{len(resultados)} ({sucessos/len(resultados)*100:.1f}%)")
    
    if sucessos == len(resultados):
        print("🎉 TODOS OS TESTES PASSARAM - SISTEMA NOVO ESTÁ FUNCIONAL!")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM - VERIFICAR LOGS ACIMA")
    
    return sucessos == len(resultados)

if __name__ == "__main__":
    main() 