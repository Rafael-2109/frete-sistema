#!/usr/bin/env python3
"""
Script de inicialização do Servidor MCP para Sistema de Fretes
Execute este script para iniciar o servidor MCP
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def verificar_dependencias():
    """Verifica se as dependências MCP estão instaladas"""
    try:
        import mcp
        import pydantic
        import anyio
        print("✅ Dependências MCP encontradas")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("Execute: pip install -r requirements.txt")
        return False

def verificar_estrutura():
    """Verifica se a estrutura do projeto está correta"""
    arquivos_necessarios = [
        'mcp_server.py',
        'mcp_config.json'
    ]
    
    for arquivo in arquivos_necessarios:
        if not os.path.exists(arquivo):
            print(f"❌ Arquivo não encontrado: {arquivo}")
            return False
    
    print("✅ Estrutura MCP verificada")
    return True

def verificar_sistema_flask():
    """Verifica se o sistema Flask pode ser importado"""
    try:
        # Adiciona o diretório pai ao path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Testa importação dos principais modelos
            from app.embarques.models import Embarque
            from app.fretes.models import Frete
            from app.monitoramento.models import EntregaMonitorada
            print("✅ Sistema Flask carregado com sucesso")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao carregar sistema Flask: {e}")
        return False

def mostrar_info_configuracao():
    """Mostra informações sobre como configurar clientes MCP"""
    
    config_claude = {
        "mcpServers": {
            "frete-sistema": {
                "command": "python",
                "args": ["mcp/mcp_server.py"],
                "cwd": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "env": {
                    "FLASK_ENV": "development"
                }
            }
        }
    }
    
    print("\n" + "="*60)
    print("📋 CONFIGURAÇÃO PARA CLAUDE DESKTOP")
    print("="*60)
    print("Adicione esta configuração no arquivo claude_desktop_config.json:")
    print(json.dumps(config_claude, indent=2))
    
    print("\n" + "="*60)
    print("📁 LOCALIZAÇÃO DO ARQUIVO DE CONFIGURAÇÃO")
    print("="*60)
    
    # Detecta o sistema operacional
    if os.name == 'nt':  # Windows
        config_path = os.path.expanduser("~\\AppData\\Roaming\\Claude\\claude_desktop_config.json")
        print(f"Windows: {config_path}")
    elif sys.platform == 'darwin':  # macOS
        config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
        print(f"macOS: {config_path}")
    else:  # Linux
        config_path = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")
        print(f"Linux: {config_path}")
    
    print("\n" + "="*60)
    print("🚀 COMO TESTAR")
    print("="*60)
    print("1. Adicione a configuração acima no arquivo do Claude Desktop")
    print("2. Reinicie o Claude Desktop")
    print("3. Em uma nova conversa, teste com:")
    print("   - 'Quais embarques estão ativos?'")
    print("   - 'Mostre estatísticas dos últimos 7 dias'")
    print("   - 'Há fretes pendentes de aprovação?'")

def main():
    """Função principal"""
    print("🚀 Iniciando Servidor MCP - Sistema de Fretes")
    print("="*50)
    
    # Verificações
    if not verificar_dependencias():
        return 1
    
    if not verificar_estrutura():
        return 1
    
    if not verificar_sistema_flask():
        return 1
    
    print("\n✅ Todas as verificações passaram!")
    
    # Mostra informações de configuração
    mostrar_info_configuracao()
    
    print("\n" + "="*60)
    print("🔄 INICIANDO SERVIDOR MCP...")
    print("="*60)
    print("Pressione Ctrl+C para parar")
    
    try:
        # Inicia o servidor MCP
        from mcp_server import main as run_server
        import asyncio
        asyncio.run(run_server())
        
    except KeyboardInterrupt:
        print("\n\n👋 Servidor MCP finalizado")
        return 0
    except Exception as e:
        print(f"\n❌ Erro ao executar servidor: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 