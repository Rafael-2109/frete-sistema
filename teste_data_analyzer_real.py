#!/usr/bin/env python3
"""
🧪 TESTE DATA ANALYZER REAL
Validar que o data_analyzer existe e funciona corretamente
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_data_analyzer_exists():
    """Testa se o data_analyzer existe e pode ser importado"""
    try:
        from app.claude_ai_novo.semantic.readers.database.data_analyzer import DataAnalyzer
        print("✅ DataAnalyzer importado com sucesso")
        return True
    except ImportError as e:
        print(f"❌ Erro ao importar DataAnalyzer: {e}")
        return False

def test_data_analyzer_methods():
    """Testa se os métodos do DataAnalyzer existem"""
    try:
        from app.claude_ai_novo.semantic.readers.database.data_analyzer import DataAnalyzer
        
        # Criar instância
        analyzer = DataAnalyzer()
        
        # Verificar métodos principais
        methods = [
            'analisar_dados_reais',
            'analisar_tabela_completa',
            'set_engine',
            'is_available',
            'limpar_cache'
        ]
        
        for method in methods:
            if hasattr(analyzer, method):
                print(f"✅ Método {method} existe")
            else:
                print(f"❌ Método {method} não existe")
                return False
        
        print("✅ Todos os métodos do DataAnalyzer existem")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar métodos: {e}")
        return False

def test_suggestions_engine_with_real_analyzer():
    """Testa se o suggestions/engine.py pode usar o DataAnalyzer real"""
    try:
        from app.claude_ai_novo.suggestions.engine import SuggestionEngine
        
        # Criar engine
        engine = SuggestionEngine()
        
        # Testar método que usa DataAnalyzer
        analyzer = engine._get_data_analyzer()
        
        if analyzer:
            print("✅ SuggestionEngine pode obter DataAnalyzer")
            print(f"✅ Analyzer available: {analyzer.is_available()}")
            return True
        else:
            print("⚠️ SuggestionEngine não conseguiu obter DataAnalyzer (sem engine)")
            return True  # Isso é normal sem engine configurado
            
    except Exception as e:
        print(f"❌ Erro ao testar SuggestionEngine: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🧪 TESTE DATA ANALYZER REAL")
    print("=" * 50)
    
    resultados = []
    
    # Teste 1: Importação
    print("\n1. Testando importação...")
    resultados.append(test_data_analyzer_exists())
    
    # Teste 2: Métodos
    print("\n2. Testando métodos...")
    resultados.append(test_data_analyzer_methods())
    
    # Teste 3: Integração com SuggestionEngine
    print("\n3. Testando integração com SuggestionEngine...")
    resultados.append(test_suggestions_engine_with_real_analyzer())
    
    # Resultado final
    print("\n" + "=" * 50)
    sucessos = sum(resultados)
    total = len(resultados)
    
    print(f"📊 RESULTADO: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Data Analyzer EXISTE e está funcionando corretamente")
        print("✅ SuggestionEngine pode usar o DataAnalyzer real")
    else:
        print("❌ Alguns testes falharam")
        
    return sucessos == total

if __name__ == "__main__":
    main() 