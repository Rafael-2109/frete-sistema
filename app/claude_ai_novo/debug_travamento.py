#!/usr/bin/env python3
"""
🔍 DEBUG DO TRAVAMENTO
=====================

Identifica exatamente onde o sistema está travando.
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def debug_imports():
    """Debug passo a passo dos imports"""
    print("\n🔍 DEBUG DETALHADO DO TRAVAMENTO\n")
    
    # Teste 1: Import básico
    print("1️⃣ Testando import do módulo integration...")
    try:
        import app.claude_ai_novo.integration
        print("   ✅ Import do módulo OK")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    # Teste 2: Import do __init__.py
    print("\n2️⃣ Testando import do __init__.py da integration...")
    try:
        # Vamos importar diretamente o arquivo para ver onde trava
        integration_init = Path(__file__).parent / "integration" / "__init__.py"
        print(f"   Arquivo: {integration_init}")
        print(f"   Existe: {integration_init.exists()}")
        
        # Ler o arquivo para ver o conteúdo
        if integration_init.exists():
            with open(integration_init, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print(f"   Linhas no arquivo: {len(lines)}")
            
            # Procurar imports problemáticos
            print("\n   🔍 Analisando imports no __init__.py:")
            for i, line in enumerate(lines[:50]):  # Primeiras 50 linhas
                if "import" in line and not line.strip().startswith("#"):
                    print(f"      Linha {i+1}: {line.strip()}")
    except Exception as e:
        print(f"   ❌ Erro ao ler arquivo: {e}")
    
    # Teste 3: Import direto do IntegrationManager
    print("\n3️⃣ Testando import direto do integration_manager.py...")
    try:
        # Adicionar debug antes do import
        print("   Tentando importar integration_manager...")
        
        # Vamos verificar se o arquivo existe
        manager_file = Path(__file__).parent / "integration" / "integration_manager.py"
        print(f"   Arquivo existe: {manager_file.exists()}")
        
        # Tentar import direto
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        print("   ✅ Import da classe IntegrationManager OK")
        
    except Exception as e:
        print(f"   ❌ Erro no import: {e}")
        import traceback
        traceback.print_exc()
    
    # Teste 4: Verificar se é o get_integration_manager
    print("\n4️⃣ Testando import do get_integration_manager...")
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        print("   ✅ Import da função get_integration_manager OK")
        
        # Testar criação de instância
        print("\n5️⃣ Testando criação de instância...")
        manager = get_integration_manager()
        print("   ✅ Instância criada com sucesso!")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    # Teste 6: Verificar orchestrators
    print("\n6️⃣ Verificando se o problema está nos orchestrators...")
    try:
        print("   Testando import do módulo orchestrators...")
        import app.claude_ai_novo.orchestrators
        print("   ✅ Import do módulo orchestrators OK")
        
        # Verificar __init__.py dos orchestrators
        orch_init = Path(__file__).parent / "orchestrators" / "__init__.py"
        if orch_init.exists():
            with open(orch_init, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Procurar imports problemáticos
            if "import" in content:
                print("\n   🔍 Imports encontrados no orchestrators/__init__.py:")
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "from ." in line and "import" in line:
                        print(f"      Linha {i+1}: {line.strip()}")
        
    except Exception as e:
        print(f"   ❌ Erro nos orchestrators: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("📊 ANÁLISE DO TRAVAMENTO")
    print("="*60)
    
    print("\nPOSSÍVEIS CAUSAS:")
    print("1. Import circular entre módulos")
    print("2. Inicialização pesada durante import")
    print("3. Dependência de recursos externos (Redis, DB)")
    print("4. Loop infinito em algum __init__.py")
    
    print("\n🔍 PRÓXIMO PASSO:")
    print("Verificar os logs acima para identificar onde parou")

if __name__ == "__main__":
    debug_imports() 