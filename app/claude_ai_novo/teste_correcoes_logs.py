#!/usr/bin/env python3
"""
🔧 TESTE DAS CORREÇÕES DOS LOGS
============================

Script para testar as correções aplicadas aos problemas identificados nos logs.
"""

import sys
import traceback
from datetime import datetime

def test_processors_imports():
    """Testa os imports dos processors"""
    print("🔧 Testando imports dos processors...")
    
    try:
        # Teste 1: date import em base.py
        from app.claude_ai_novo.processors.base import date
        print("✅ date importado com sucesso de processors.base")
        
        # Teste 2: get_context_processor (alias)
        from app.claude_ai_novo.processors.context_processor import get_context_processor
        print("✅ get_context_processor importado com sucesso")
        
        # Teste 3: get_query_processor
        from app.claude_ai_novo.processors.query_processor import get_query_processor
        print("✅ get_query_processor importado com sucesso")
        
        # Teste 4: Instanciar processors
        context_proc = get_context_processor()
        query_proc = get_query_processor()
        
        print(f"✅ ContextProcessor: {type(context_proc)}")
        print(f"✅ QueryProcessor: {type(query_proc)}")
        
    except Exception as e:
        print(f"❌ Erro nos imports dos processors: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_performance_cache():
    """Testa o PerformanceCache"""
    print("\n🚀 Testando PerformanceCache...")
    
    try:
        # Teste 1: Import da classe
        from app.claude_ai_novo.utils.performance_cache import PerformanceCache
        print("✅ PerformanceCache importado com sucesso")
        
        # Teste 2: Instanciar
        cache = PerformanceCache()
        print(f"✅ PerformanceCache instanciado: {type(cache)}")
        
        # Teste 3: Métodos básicos
        stats = cache.get_cache_stats()
        print(f"✅ Cache stats: {stats}")
        
    except Exception as e:
        print(f"❌ Erro no PerformanceCache: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_pattern_learning():
    """Testa o PatternLearning"""
    print("\n🎯 Testando PatternLearning...")
    
    try:
        # Teste 1: Import
        from app.claude_ai_novo.learners.pattern_learning import get_pattern_learner
        print("✅ get_pattern_learner importado")
        
        # Teste 2: Instanciar
        learner = get_pattern_learner()
        print(f"✅ PatternLearner instanciado: {type(learner)}")
        
        # Teste 3: Testar método sem banco (deve falhar graciosamente)
        padroes = learner.extrair_e_salvar_padroes("teste", {"dominio": "test"})
        print(f"✅ Método chamado sem erro: {len(padroes)} padrões")
        
    except Exception as e:
        print(f"❌ Erro no PatternLearning: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_all_imports():
    """Testa todos os imports críticos"""
    print("\n🔍 Testando imports críticos...")
    
    critical_imports = [
        "app.claude_ai_novo.processors.base",
        "app.claude_ai_novo.processors.context_processor", 
        "app.claude_ai_novo.processors.query_processor",
        "app.claude_ai_novo.utils.performance_cache",
        "app.claude_ai_novo.learners.pattern_learning",
        "app.claude_ai_novo.learners.learning_core",
        "app.claude_ai_novo.utils.validation_utils",
        "app.claude_ai_novo.utils.utils_manager"
    ]
    
    success_count = 0
    
    for import_path in critical_imports:
        try:
            __import__(import_path)
            print(f"✅ {import_path}")
            success_count += 1
        except Exception as e:
            print(f"❌ {import_path}: {e}")
    
    print(f"\n📊 Resultado: {success_count}/{len(critical_imports)} imports bem-sucedidos")
    return success_count == len(critical_imports)

def main():
    """Função principal de teste"""
    print("🧪 TESTE DAS CORREÇÕES DOS LOGS")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Executar testes
    results.append(("Processors Imports", test_processors_imports()))
    results.append(("PerformanceCache", test_performance_cache()))
    results.append(("PatternLearning", test_pattern_learning()))
    results.append(("All Critical Imports", test_all_imports()))
    
    # Relatório final
    print("\n" + "=" * 40)
    print("📋 RELATÓRIO FINAL")
    print("=" * 40)
    
    for test_name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    total_success = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\nTotal: {total_success}/{total_tests} testes passaram")
    
    if total_success == total_tests:
        print("🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 