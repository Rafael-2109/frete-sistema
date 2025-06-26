#!/usr/bin/env python3
"""
Script para resolver problemas visuais de importação no VS Code
"""

import os
import json
import subprocess
import sys
import shutil

def criar_configuracoes_vscode():
    """Cria/atualiza configurações do VS Code"""
    print("🔧 Configurando VS Code...")
    
    # Criar diretório .vscode se não existir
    vscode_dir = ".vscode"
    if not os.path.exists(vscode_dir):
        os.makedirs(vscode_dir)
        print(f"✅ Criado diretório {vscode_dir}")
    
    # Configurações do VS Code
    settings = {
        "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
        "python.analysis.extraPaths": [
            "./",
            "./app",
            "./app/utils"
        ],
        "python.analysis.autoImportCompletions": True,
        "python.analysis.typeCheckingMode": "basic",
        "python.linting.enabled": True,
        "python.linting.pylintEnabled": False,
        "python.linting.flake8Enabled": True,
        "python.analysis.autoSearchPaths": True,
        "python.analysis.diagnosticMode": "workspace",
        "python.terminal.activateEnvironment": True,
        "files.exclude": {
            "**/__pycache__": True,
            "**/*.pyc": True
        },
        "python.analysis.stubPath": "./typings",
        "python.analysis.packageIndexDepths": [
            {"name": "app", "depth": 10}
        ]
    }
    
    settings_path = os.path.join(vscode_dir, "settings.json")
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)
    print(f"✅ Criado {settings_path}")

def criar_pyrightconfig():
    """Cria configuração do Pylance/Pyright"""
    print("🔧 Configurando Pylance...")
    
    config = {
        "include": ["app"],
        "exclude": [
            "**/node_modules",
            "**/__pycache__",
            "**/*.pyc"
        ],
        "extraPaths": [
            "./",
            "./app",
            "./app/utils"
        ],
        "pythonVersion": "3.11",
        "pythonPlatform": "Windows",
        "typeCheckingMode": "basic",
        "useLibraryCodeForTypes": True,
        "autoImportCompletions": True,
        "autoSearchPaths": True,
        "reportMissingImports": "warning",
        "reportMissingTypeStubs": "none",
        "reportGeneralTypeIssues": "none",
        "reportOptionalMemberAccess": "none",
        "reportPrivateImportUsage": "none"
    }
    
    with open("pyrightconfig.json", 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print("✅ Criado pyrightconfig.json")

def verificar_py_typed():
    """Verifica se arquivos py.typed existem"""
    print("🔧 Verificando marcadores de type hints...")
    
    # Arquivo py.typed na raiz do app
    app_typed = "app/py.typed"
    if not os.path.exists(app_typed):
        with open(app_typed, 'w') as f:
            f.write("# Marker file for PEP 561 - This package supports type hints\n")
        print(f"✅ Criado {app_typed}")
    
    # Arquivo py.typed em utils
    utils_typed = "app/utils/py.typed"
    if not os.path.exists(utils_typed):
        with open(utils_typed, 'w') as f:
            f.write("# Marker file for PEP 561\n")
        print(f"✅ Criado {utils_typed}")

def verificar_ambiente_virtual():
    """Verifica se o ambiente virtual está configurado"""
    print("🔧 Verificando ambiente virtual...")
    
    venv_python = os.path.join("venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        print("✅ Ambiente virtual encontrado")
        return True
    else:
        print("❌ Ambiente virtual não encontrado em venv/Scripts/python.exe")
        return False

def testar_importacoes():
    """Testa se as importações funcionam"""
    print("🧪 Testando importações...")
    
    try:
        # Testa importação direta
        from app.utils.valores_brasileiros import converter_valor_brasileiro
        print("✅ Importação direta funcionando")
        
        # Testa importação via __init__
        from app.utils import converter_valor_brasileiro as conv
        print("✅ Importação via __init__ funcionando")
        
        # Testa as funções
        resultado = converter_valor_brasileiro("1.234,56")
        if resultado == 1234.56:
            print("✅ Função converter_valor_brasileiro funcionando")
        else:
            print(f"⚠️ Resultado inesperado: {resultado}")
            
        return True
        
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

def limpar_cache_python():
    """Remove cache Python para forçar reimportação"""
    print("🧹 Limpando cache Python...")
    
    cache_dirs = []
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                cache_dirs.append(os.path.join(root, d))
    
    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir)
            print(f"✅ Removido {cache_dir}")
        except Exception as e:
            print(f"⚠️ Não foi possível remover {cache_dir}: {e}")

def main():
    """Função principal"""
    print("🚀 Resolvendo problemas visuais do VS Code...")
    print("=" * 50)
    
    # 1. Verificar ambiente
    if not verificar_ambiente_virtual():
        print("\n❌ Configure o ambiente virtual primeiro:")
        print("   python -m venv venv")
        print("   .\\venv\\Scripts\\activate")
        print("   pip install -r requirements.txt")
        return
    
    # 2. Limpar cache
    limpar_cache_python()
    
    # 3. Criar configurações
    criar_configuracoes_vscode()
    criar_pyrightconfig()
    verificar_py_typed()
    
    # 4. Testar importações
    print("\n🧪 Verificando funcionalidade...")
    if testar_importacoes():
        print("\n✅ SUCESSO! Importações funcionando corretamente.")
    else:
        print("\n⚠️ Há problemas com as importações.")
    
    print("\n🔄 PRÓXIMOS PASSOS para resolver problemas visuais:")
    print("1. Feche completamente o VS Code")
    print("2. Reabra o VS Code")
    print("3. Pressione Ctrl+Shift+P")
    print("4. Digite 'Python: Select Interpreter'")
    print("5. Selecione: .\\venv\\Scripts\\python.exe")
    print("6. Pressione Ctrl+Shift+P novamente")
    print("7. Digite 'Developer: Reload Window'")
    print("8. Se ainda houver problemas, pressione Ctrl+Shift+P")
    print("9. Digite 'Pylance: Clear Cache and Reload Window'")
    
    print("\n📝 Arquivos criados/atualizados:")
    print("   - .vscode/settings.json")
    print("   - pyrightconfig.json")
    print("   - app/py.typed")
    print("   - app/utils/py.typed")

if __name__ == "__main__":
    main() 