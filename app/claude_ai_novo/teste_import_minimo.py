#!/usr/bin/env python3
"""
🧪 TESTE MÍNIMO DE IMPORT
========================

Identifica exatamente qual import está causando o travamento.
"""

import os
import sys
import time
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def teste_minimo():
    """Testa imports mínimos"""
    print("\n🧪 TESTE MÍNIMO DE IMPORT\n")
    
    # Teste 1: Import do módulo claude_ai_novo
    print("1️⃣ Testando import app.claude_ai_novo...")
    start = time.time()
    try:
        import app.claude_ai_novo
        print(f"   ✅ OK em {time.time() - start:.2f}s")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    # Teste 2: Import do integration diretamente
    print("\n2️⃣ Testando import app.claude_ai_novo.integration...")
    start = time.time()
    try:
        import app.claude_ai_novo.integration
        print(f"   ✅ OK em {time.time() - start:.2f}s")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    # Teste 3: Import do get_integration_manager via __init__.py
    from app.claude_ai_novo.integration.integration_manager import get_integration_manager
    start = time.time()
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        print(f"   ✅ OK em {time.time() - start:.2f}s")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    # Teste 4: Criar instância
    print("\n4️⃣ Testando criação de instância...")
    start = time.time()
    try:
        manager = get_integration_manager()
        print(f"   ✅ OK em {time.time() - start:.2f}s")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    print("\n✅ TODOS OS TESTES PASSARAM!")
    print("O problema não está nos imports diretos.")
    
    # Teste 5: Verificar se é o get_claude_ai_instance
    print("\n5️⃣ Testando get_claude_ai_instance...")
    start = time.time()
    try:
        from app.claude_ai_novo import get_claude_ai_instance
        print(f"   ✅ Import OK em {time.time() - start:.2f}s")
        
        # NÃO chamar a função, pois ela pode travar
        print("   ⚠️ NÃO vamos chamar get_claude_ai_instance() pois pode travar")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Teste 6: Verificar se o problema é o import do db
    print("\n6️⃣ Testando import app (pode travar aqui)...")
    start = time.time()
    try:
        import app
        print(f"   ✅ OK em {time.time() - start:.2f}s")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        print("   💡 O problema pode estar na inicialização do Flask app")

if __name__ == "__main__":
    teste_minimo() 