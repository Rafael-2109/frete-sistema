#!/usr/bin/env python3
"""
Script para resolver definitivamente os 1000+ erros no VS Code
Configura corretamente o ambiente Python e as extensões
"""

import os
import json
import sys
import subprocess
from pathlib import Path

def obter_caminho_projeto():
    """Obter caminho absoluto do projeto"""
    return Path(__file__).parent.absolute()

def obter_caminho_python_venv():
    """Obter caminho do Python no ambiente virtual"""
    projeto_path = obter_caminho_projeto()
    if os.name == 'nt':  # Windows
        python_path = projeto_path / "venv" / "Scripts" / "python.exe"
    else:  # Linux/Mac
        python_path = projeto_path / "venv" / "bin" / "python"
    
    return str(python_path.resolve())

def criar_configuracao_vscode():
    """Criar configurações do VS Code"""
    projeto_path = obter_caminho_projeto()
    vscode_dir = projeto_path / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    
    python_path = obter_caminho_python_venv()
    
    # Configurações principais
    settings = {
        "python.interpreterPath": python_path,
        "python.defaultInterpreterPath": python_path,
        "python.terminal.activateEnvironment": True,
        "python.terminal.activateEnvInCurrentTerminal": True,
        "python.analysis.extraPaths": [
            "${workspaceFolder}/app",
            "${workspaceFolder}/app/utils",
            "${workspaceFolder}",
            "${workspaceFolder}/venv/Lib/site-packages"
        ],
        "python.analysis.autoImportCompletions": True,
        "python.analysis.autoSearchPaths": True,
        "python.analysis.diagnosticMode": "workspace",
        "python.analysis.useLibraryCodeForTypes": True,
        "python.linting.enabled": True,
        "python.linting.pylintEnabled": False,
        "python.linting.flake8Enabled": True,
        "python.linting.flake8Args": [
            "--max-line-length=120",
            "--ignore=E501,W503"
        ],
        "pylance.insidersChannel": "off",
        "python.analysis.typeCheckingMode": "basic",
        "python.analysis.completeFunctionParens": True,
        "python.analysis.indexing": True,
        "files.associations": {
            "*.py": "python"
        },
        "python.formatting.provider": "black",
        "editor.formatOnSave": False,
        "python.linting.lintOnSave": True
    }
    
    settings_file = vscode_dir / "settings.json"
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Configurações salvas em: {settings_file}")

def criar_arquivo_workspace():
    """Criar arquivo de workspace"""
    projeto_path = obter_caminho_projeto()
    python_path = obter_caminho_python_venv()
    
    workspace = {
        "folders": [
            {
                "name": "Sistema de Fretes",
                "path": "."
            }
        ],
        "settings": {
            "python.interpreterPath": python_path,
            "python.defaultInterpreterPath": python_path,
            "python.analysis.extraPaths": [
                "${workspaceFolder}/app",
                "${workspaceFolder}/app/utils",
                "${workspaceFolder}"
            ]
        },
        "extensions": {
            "recommendations": [
                "ms-python.python",
                "ms-python.pylance",
                "ms-python.black-formatter",
                "ms-python.flake8"
            ]
        }
    }
    
    workspace_file = projeto_path / "frete-sistema.code-workspace"
    with open(workspace_file, 'w', encoding='utf-8') as f:
        json.dump(workspace, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Workspace criado: {workspace_file}")

def criar_pyproject_toml():
    """Criar configuração pyproject.toml para ferramentas Python"""
    projeto_path = obter_caminho_projeto()
    
    pyproject_content = """[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "frete-sistema"
version = "1.0.0"
description = "Sistema de Gestão de Fretes"
readme = "README.md"
requires-python = ">=3.8"

[tool.black]
line-length = 120
target-version = ['py38']
include = '\\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 120
"""
    
    pyproject_file = projeto_path / "pyproject.toml"
    with open(pyproject_file, 'w', encoding='utf-8') as f:
        f.write(pyproject_content)
    
    print(f"✅ pyproject.toml criado: {pyproject_file}")

def verificar_dependencias():
    """Verificar se todas as dependências estão instaladas"""
    print("🔍 Verificando dependências...")
    
    dependencias_criticas = [
        'flask', 'sqlalchemy', 'wtforms', 'flask-wtf',
        'flask-sqlalchemy', 'flask-migrate', 'werkzeug'
    ]
    
    missing = []
    for dep in dependencias_criticas:
        try:
            __import__(dep.replace('-', '_'))
            print(f"  ✅ {dep}")
        except ImportError:
            missing.append(dep)
            print(f"  ❌ {dep}")
    
    if missing:
        print(f"\n❌ Dependências faltando: {', '.join(missing)}")
        print("Execute: pip install -r requirements.txt")
        return False
    
    print("✅ Todas as dependências críticas estão instaladas")
    return True

def limpar_cache_python():
    """Limpar cache Python"""
    print("🧹 Limpando cache Python...")
    
    projeto_path = obter_caminho_projeto()
    
    # Remover __pycache__
    for pycache in projeto_path.glob("**/__pycache__"):
        if pycache.is_dir():
            import shutil
            shutil.rmtree(pycache)
            print(f"  🗑️  Removido: {pycache}")
    
    # Remover .pyc files
    pyc_count = 0
    for pyc_file in projeto_path.glob("**/*.pyc"):
        pyc_file.unlink()
        pyc_count += 1
    
    if pyc_count > 0:
        print(f"  🗑️  Removidos {pyc_count} arquivos .pyc")
    
    print("✅ Cache Python limpo")

def main():
    """Função principal"""
    print("🚀 CONFIGURANDO VS CODE PARA RESOLVER 1000+ ERROS")
    print("=" * 60)
    
    # Verificar se estamos no diretório correto
    projeto_path = obter_caminho_projeto()
    print(f"📁 Projeto: {projeto_path}")
    
    # Verificar Python do venv
    python_path = obter_caminho_python_venv()
    print(f"🐍 Python venv: {python_path}")
    
    if not Path(python_path).exists():
        print("❌ ERRO: Python do venv não encontrado!")
        print("Execute primeiro: python -m venv venv")
        return False
    
    # Verificar dependências
    if not verificar_dependencias():
        return False
    
    # Limpar cache
    limpar_cache_python()
    
    # Criar configurações
    criar_configuracao_vscode()
    criar_arquivo_workspace()
    criar_pyproject_toml()
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURAÇÃO CONCLUÍDA!")
    print("\nPASOS FINAIS:")
    print("1. 📄 Abra o arquivo: frete-sistema.code-workspace")  
    print("2. 🔄 No VS Code: Ctrl+Shift+P → 'Python: Select Interpreter'")
    print("3. 🎯 Selecione: ./venv/Scripts/python.exe")
    print("4. 🔄 Reinicie o VS Code: Ctrl+Shift+P → 'Developer: Reload Window'")
    print("5. ⏱️  Aguarde alguns minutos para o Pylance indexar")
    
    print(f"\n🎯 Python configurado: {python_path}")
    print("🚀 Os 1000+ erros devem desaparecer!")

if __name__ == "__main__":
    main() 