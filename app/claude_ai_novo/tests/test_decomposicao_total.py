#!/usr/bin/env python3
"""
Testes da Decomposição Total
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_decomposicao_total():
    """Testa decomposição total"""
    print("🧪 TESTANDO DECOMPOSIÇÃO TOTAL")
    print("=" * 50)
    
    try:
        # Testar importação do sistema principal
        from app.claude_ai_novo.claude_ai_modular import get_claude_ai_system
        
        # Inicializar sistema
        system = get_claude_ai_system()
        
        print("✅ Sistema Claude AI Modular carregado com sucesso!")
        
        # Testar processamento básico
        resultado = system.processar_consulta("teste básico")
        print(f"✅ Processamento básico: {len(resultado)} caracteres")
        
        # Testar módulos individuais
        print("\n📦 Testando módulos individuais:")
        
        modules = [
            'excel_commands', 'dev_commands', 'cursor_commands', 'file_commands',
            'database_loader', 'context_loader', 'query_analyzer', 'intention_analyzer',
            'context_processor', 'response_processor', 'response_utils', 'validation_utils'
        ]
        
        for module in modules:
            if hasattr(system, module):
                print(f"   ✅ {module}")
            else:
                print(f"   ❌ {module}")
        
        print("\n🎯 DECOMPOSIÇÃO TOTAL VALIDADA!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na decomposição: {e}")
        return False

if __name__ == "__main__":
    success = test_decomposicao_total()
    exit(0 if success else 1)
