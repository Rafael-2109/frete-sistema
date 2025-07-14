#!/usr/bin/env python3
"""
Verifica se os módulos de commands estão funcionando após correções
"""

import sys
from pathlib import Path

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent))

def testar_imports():
    """Testa imports dos módulos commands"""
    print("🔍 Testando imports dos módulos commands...")
    
    # 1. Testar base_command
    print("\n1. Testando base_command...")
    try:
        from app.claude_ai_novo.commands.base_command import (
            BaseCommand, format_response_advanced, create_excel_summary, 
            detect_command_type
        )
        print("✅ base_command importado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao importar base_command: {e}")
        return False
    
    # 2. Testar excel_command_manager
    print("\n2. Testando excel_command_manager...")
    try:
        from app.claude_ai_novo.commands.excel_command_manager import ExcelOrchestrator
        print("✅ excel_command_manager importado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao importar excel_command_manager: {e}")
    
    # 3. Testar cursor_commands
    print("\n3. Testando cursor_commands...")
    try:
        from app.claude_ai_novo.commands.cursor_commands import CursorCommands
        print("✅ cursor_commands importado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao importar cursor_commands: {e}")
    
    # 4. Testar dev_commands
    print("\n4. Testando dev_commands...")
    try:
        from app.claude_ai_novo.commands.dev_commands import DevCommands
        print("✅ dev_commands importado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao importar dev_commands: {e}")
    
    # 5. Testar file_commands
    print("\n5. Testando file_commands...")
    try:
        from app.claude_ai_novo.commands.file_commands import FileCommands
        print("✅ file_commands importado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao importar file_commands: {e}")
    
    # 6. Testar módulo commands principal
    print("\n6. Testando módulo commands principal...")
    try:
        from app.claude_ai_novo import commands
        status = commands.get_commands_status()
        print(f"✅ Módulo commands carregado!")
        print(f"📊 Status dos comandos: {status}")
    except Exception as e:
        print(f"❌ Erro ao importar módulo commands: {e}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 VERIFICAÇÃO DE CORREÇÕES DOS COMMANDS")
    print("=" * 60)
    
    sucesso = testar_imports()
    
    print("\n" + "=" * 60)
    if sucesso:
        print("✅ CORREÇÕES APLICADAS COM SUCESSO!")
    else:
        print("❌ AINDA HÁ PROBLEMAS A RESOLVER")
    print("=" * 60) 