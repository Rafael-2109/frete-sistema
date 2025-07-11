#!/usr/bin/env python3
"""
🔧 TESTE SIMPLES DAS CORREÇÕES
============================

Script simples para testar as correções aplicadas.
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório app ao sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_date_import():
    """Testa o import de date"""
    print("🔧 Testando import de date...")
    
    try:
        from app.claude_ai_novo.processors.base import date
        print("✅ date importado com sucesso")
        
        # Testar uso da date
        today = date.today()
        print(f"✅ date funcionando: {today}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no import de date: {e}")
        return False

def test_context_processor_alias():
    """Testa o alias do context processor"""
    print("\n🔧 Testando alias do context processor...")
    
    try:
        from app.claude_ai_novo.processors.context_processor import get_context_processor
        print("✅ get_context_processor importado")
        
        # Testar instanciação
        processor = get_context_processor()
        print(f"✅ Instanciado: {type(processor)}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no context processor: {e}")
        return False

def test_query_processor_function():
    """Testa a função do query processor"""
    print("\n🔧 Testando função do query processor...")
    
    try:
        from app.claude_ai_novo.processors.query_processor import get_query_processor
        print("✅ get_query_processor importado")
        
        # Testar instanciação
        processor = get_query_processor()
        print(f"✅ Instanciado: {type(processor)}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no query processor: {e}")
        return False

def test_performance_cache_alias():
    """Testa o alias do performance cache"""
    print("\n🔧 Testando alias do performance cache...")
    
    try:
        from app.claude_ai_novo.utils.performance_cache import PerformanceCache
        print("✅ PerformanceCache importado")
        
        # Testar instanciação
        cache = PerformanceCache()
        print(f"✅ Instanciado: {type(cache)}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no performance cache: {e}")
        return False

def test_imports_structure():
    """Testa a estrutura dos imports"""
    print("\n🔧 Testando estrutura dos imports...")
    
    success_count = 0
    total_tests = 0
    
    # Testar imports básicos
    test_imports = [
        ("processors.base", "from app.claude_ai_novo.processors.base import ProcessorBase"),
        ("performance_cache", "from app.claude_ai_novo.utils.performance_cache import ScannersCache"),
        ("pattern_learning", "from app.claude_ai_novo.learners.pattern_learning import PatternLearner"),
        ("validation_utils", "from app.claude_ai_novo.utils.validation_utils import BaseValidationUtils"),
    ]
    
    for name, import_stmt in test_imports:
        total_tests += 1
        try:
            exec(import_stmt)
            print(f"✅ {name}")
            success_count += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    print(f"\n📊 Resultado: {success_count}/{total_tests} imports bem-sucedidos")
    return success_count == total_tests

def main():
    """Função principal"""
    print("🧪 TESTE SIMPLES DAS CORREÇÕES")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Executar testes
    results.append(("Date Import", test_date_import()))
    results.append(("Context Processor Alias", test_context_processor_alias()))
    results.append(("Query Processor Function", test_query_processor_function()))
    results.append(("Performance Cache Alias", test_performance_cache_alias()))
    results.append(("Imports Structure", test_imports_structure()))
    
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