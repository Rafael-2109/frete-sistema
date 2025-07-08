#!/usr/bin/env python3
"""
Teste específico do sistema novo
"""

import sys
from pathlib import Path
projeto_root = Path(__file__).parent
sys.path.insert(0, str(projeto_root))

def testar_sistema_novo():
    print("🧪 TESTANDO SISTEMA NOVO")
    print("="*40)
    
    try:
        # Teste 1: Importar excel_commands
        print("1. Testando excel_commands...")
        from app.claude_ai_novo.commands.excel_commands import get_excel_commands
        print("   ✅ excel_commands OK")
        
        # Teste 2: Importar database_loader
        print("2. Testando database_loader...")
        from app.claude_ai_novo.data_loaders.database_loader import get_database_loader
        print("   ✅ database_loader OK")
        
        # Teste 3: Importar claude_integration
        print("3. Testando claude_integration...")
        from app.claude_ai_novo.integration.claude import get_claude_integration
        print("   ✅ claude_integration OK")
        
        # Teste 4: Testar interface de transição
        print("4. Testando interface de transição...")
        from app.claude_transition import get_claude_transition
        transition = get_claude_transition()
        print(f"   ✅ Sistema ativo: {transition.sistema_ativo}")
        
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    testar_sistema_novo() 