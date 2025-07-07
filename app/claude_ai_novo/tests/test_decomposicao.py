#!/usr/bin/env python3
"""
Teste de Validação da Decomposição
"""

import sys
import os

# Adicionar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_decomposicao():
    """Testa decomposição"""
    print("🧪 TESTANDO DECOMPOSIÇÃO MODULAR")
    print("=" * 40)
    
    try:
        # Testar import
        from app.claude_ai_novo.claude_ai_modular import processar_consulta_modular
        print("✅ Import principal funcionando")
        
        # Testar processamento
        resultado = processar_consulta_modular("teste básico")
        print(f"✅ Processamento: {len(resultado)} caracteres")
        
        print("\n🎯 DECOMPOSIÇÃO VALIDADA!")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    success = test_decomposicao()
    exit(0 if success else 1)
