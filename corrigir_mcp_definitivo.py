#!/usr/bin/env python3
"""
CORRIGIR MCP DEFINITIVO
Script para resolver o problema "spawn venv\Scripts\python.exe ENOENT" no Claude Desktop
"""

import os
import json
import shutil
from datetime import datetime

def corrigir_mcp_claude_desktop():
    """Corrige a configuracao do Claude Desktop com caminhos absolutos"""
    
    print("="*70)
    print("🔧 CORRIGINDO MCP CLAUDE DESKTOP - DEFINITIVO")
    print("="*70)
    print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # 1. Obter caminho absoluto atual
    current_path = os.getcwd()
    print(f"📂 Diretorio atual: {current_path}")
    
    # 2. Construir caminhos absolutos
    python_path = os.path.join(current_path, "venv", "Scripts", "python.exe")
    script_path = os.path.join(current_path, "mcp", "mcp_v1_9_4_atualizado.py")
    
    print(f"🐍 Python: {python_path}")
    print(f"📜 Script MCP: {script_path}")
    
    # 3. Verificar se os arquivos existem
    if not os.path.exists(python_path):
        print(f"❌ Python nao encontrado: {python_path}")
        return False
        
    if not os.path.exists(script_path):
        print(f"❌ Script MCP nao encontrado: {script_path}")
        return False
    
    print("✅ Todos os arquivos encontrados")
    
    # 4. Criar configuracao correta
    config = {
        "mcpServers": {
            "fretes-sistema": {
                "command": python_path.replace("\\", "\\\\"),
                "args": [script_path.replace("\\", "\\\\")]
            }
        }
    }
    
    # 5. Obter caminho do Claude Desktop
    appdata = os.getenv('APPDATA')
    if not appdata:
        print("❌ APPDATA nao encontrado")
        return False
        
    claude_config_path = os.path.join(appdata, 'Claude', 'claude_desktop_config.json')
    
    # 6. Fazer backup se existir
    if os.path.exists(claude_config_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(appdata, 'Claude', f'claude_desktop_config_backup_{timestamp}.json')
        shutil.copy2(claude_config_path, backup_path)
        print(f"💾 Backup criado: {backup_path}")
    
    # 7. Criar diretorio se nao existir
    os.makedirs(os.path.dirname(claude_config_path), exist_ok=True)
    
    # 8. Aplicar nova configuracao
    with open(claude_config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuracao aplicada: {claude_config_path}")
    print()
    print("🎯 CONFIGURACAO APLICADA:")
    print(f"   Servidor: fretes-sistema")
    print(f"   Comando: {python_path}")
    print(f"   Script: {script_path}")
    print()
    print("🔄 PROXIMOS PASSOS:")
    print("1. Feche completamente o Claude Desktop")
    print("2. Aguarde 5 segundos")
    print("3. Abra o Claude Desktop novamente")
    print("4. Teste com: 'Status do sistema'")
    print()
    print("✅ PROBLEMA RESOLVIDO: Caminhos absolutos aplicados!")
    
    return True

if __name__ == "__main__":
    sucesso = corrigir_mcp_claude_desktop()
    if sucesso:
        print("🎉 MCP CORRIGIDO COM SUCESSO!")
    else:
        print("❌ Erro ao corrigir MCP") 