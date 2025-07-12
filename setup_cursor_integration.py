#!/usr/bin/env python3
"""
🚀 SETUP CURSOR INTEGRATION - Configuração Automática
====================================================

Script para configurar automaticamente a integração completa do Cursor
com o Sistema de Fretes.

USAGE:
    python setup_cursor_integration.py
"""

import os
import json
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class CursorSetup:
    """Configurador automático para integração Cursor"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.vscode_dir = self.project_root / ".vscode"
        self.success_count = 0
        self.total_steps = 8
        
        print("🚀 CURSOR INTEGRATION SETUP")
        print("=" * 50)
        print(f"📁 Projeto: {self.project_root.name}")
        print(f"📍 Path: {self.project_root}")
        print("=" * 50)
    
    def create_directory(self, directory: Path) -> bool:
        """Cria diretório se não existir"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Diretório criado: {directory.name}")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar {directory.name}: {e}")
            return False
    
    def create_vscode_settings(self) -> bool:
        """Cria configurações específicas do VSCode/Cursor"""
        try:
            self.create_directory(self.vscode_dir)
            
            settings = {
                "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
                "python.linting.enabled": True,
                "python.linting.pylintEnabled": True,
                "python.terminal.activateEnvironment": True,
                "files.exclude": {
                    "**/__pycache__": True,
                    "**/*.pyc": True,
                    ".pytest_cache": True,
                    "**/migrations_backup*": True
                },
                "python.analysis.typeCheckingMode": "basic",
                "python.analysis.autoImportCompletions": True,
                "rest-client.environmentVariables": {
                    "production": {
                        "baseUrl": "https://sistema-fretes.onrender.com"
                    },
                    "local": {
                        "baseUrl": "http://localhost:5000"
                    }
                }
            }
            
            settings_file = self.vscode_dir / "settings.json"
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            
            print("✅ VSCode settings.json criado")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar settings: {e}")
            return False
    
    def create_launch_config(self) -> bool:
        """Cria configurações de debug/launch"""
        try:
            launch_config = {
                "version": "0.2.0",
                "configurations": [
                    {
                        "name": "🌐 Flask App (Debug)",
                        "type": "python",
                        "request": "launch",
                        "program": "${workspaceFolder}/run.py",
                        "env": {
                            "FLASK_ENV": "development",
                            "FLASK_DEBUG": "1",
                            "PYTHONPATH": "${workspaceFolder}"
                        },
                        "console": "integratedTerminal",
                        "justMyCode": False
                    },
                    {
                        "name": "🧪 Claude AI Tests",
                        "type": "python",
                        "request": "launch",
                        "program": "${workspaceFolder}/app/claude_ai_novo/validador_sistema_real.py",
                        "console": "integratedTerminal"
                    },
                    {
                        "name": "⚡ Quick Status",
                        "type": "python",
                        "request": "launch",
                        "program": "${workspaceFolder}/app/claude_ai_novo/check_status.py",
                        "console": "integratedTerminal"
                    }
                ]
            }
            
            launch_file = self.vscode_dir / "launch.json"
            with open(launch_file, 'w', encoding='utf-8') as f:
                json.dump(launch_config, f, indent=4)
            
            print("✅ Launch configurations criadas")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar launch config: {e}")
            return False
    
    def create_tasks_config(self) -> bool:
        """Cria configurações de tasks"""
        try:
            tasks_config = {
                "version": "2.0.0",
                "tasks": [
                    {
                        "label": "🚀 Start Flask Development",
                        "type": "shell",
                        "command": "python",
                        "args": ["run.py"],
                        "group": {
                            "kind": "build",
                            "isDefault": True
                        },
                        "presentation": {
                            "echo": True,
                            "reveal": "always",
                            "focus": False,
                            "panel": "shared"
                        },
                        "options": {
                            "env": {
                                "FLASK_ENV": "development",
                                "FLASK_DEBUG": "1"
                            }
                        }
                    },
                    {
                        "label": "🔍 Run System Validator",
                        "type": "shell",
                        "command": "python",
                        "args": ["app/claude_ai_novo/validador_sistema_real.py"],
                        "group": "test"
                    },
                    {
                        "label": "📊 System Health Check",
                        "type": "shell",
                        "command": "python",
                        "args": ["app/claude_ai_novo/check_status.py"],
                        "group": "test"
                    },
                    {
                        "label": "🔍 Monitor System",
                        "type": "shell",
                        "command": "python",
                        "args": ["app/claude_ai_novo/monitoring/cursor_monitor.py"],
                        "group": "build",
                        "presentation": {
                            "echo": True,
                            "reveal": "always",
                            "focus": True,
                            "panel": "dedicated"
                        }
                    }
                ]
            }
            
            tasks_file = self.vscode_dir / "tasks.json"
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_config, f, indent=4)
            
            print("✅ Tasks configuradas")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar tasks: {e}")
            return False
    
    def create_extensions_config(self) -> bool:
        """Cria lista de extensões recomendadas"""
        try:
            extensions_config = {
                "recommendations": [
                    "ms-python.python",
                    "ms-python.debugpy",
                    "humao.rest-client",
                    "ms-vscode.vscode-json",
                    "redhat.vscode-yaml",
                    "usernamehw.errorlens",
                    "eamodio.gitlens",
                    "ms-python.flake8",
                    "njpwerner.autodocstring"
                ]
            }
            
            extensions_file = self.vscode_dir / "extensions.json"
            with open(extensions_file, 'w', encoding='utf-8') as f:
                json.dump(extensions_config, f, indent=4)
            
            print("✅ Extensões recomendadas configuradas")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar extensions config: {e}")
            return False
    
    def create_monitor_directory(self) -> bool:
        """Cria diretório de monitoramento se necessário"""
        try:
            monitor_dir = self.project_root / "app" / "claude_ai_novo" / "monitoring"
            self.create_directory(monitor_dir)
            print("✅ Diretório de monitoramento verificado")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar diretório monitoring: {e}")
            return False
    
    def verify_files_exist(self) -> bool:
        """Verifica se arquivos essenciais existem"""
        try:
            essential_files = [
                "run.py",
                "app/claude_ai_novo/validador_sistema_real.py",
                "app/claude_ai_novo/check_status.py",
                "frete_sistema.code-workspace",
                "api_tests.http",
                ".cursorrules"
            ]
            
            missing_files = []
            for file_path in essential_files:
                if not (self.project_root / file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                print(f"⚠️ Arquivos não encontrados: {', '.join(missing_files)}")
                print("   Alguns recursos podem não funcionar completamente")
            else:
                print("✅ Todos os arquivos essenciais encontrados")
            
            return len(missing_files) == 0
            
        except Exception as e:
            print(f"❌ Erro ao verificar arquivos: {e}")
            return False
    
    def test_python_environment(self) -> bool:
        """Testa o ambiente Python"""
        try:
            # Verificar se venv existe
            venv_python = self.project_root / "venv" / "Scripts" / "python.exe"
            if not venv_python.exists():
                venv_python = self.project_root / "venv" / "bin" / "python"
            
            if venv_python.exists():
                print("✅ Virtual environment encontrado")
            else:
                print("⚠️ Virtual environment não encontrado")
                print("   Considere criar com: python -m venv venv")
            
            # Testar imports básicos
            try:
                import flask
                import requests
                print("✅ Dependências básicas (Flask, requests) disponíveis")
            except ImportError as e:
                print(f"⚠️ Dependência faltando: {e}")
                print("   Execute: pip install -r requirements.txt")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao testar ambiente Python: {e}")
            return False
    
    def create_quick_start_script(self) -> bool:
        """Cria script de quick start"""
        try:
            quick_start_content = '''#!/usr/bin/env python3
"""
🚀 QUICK START - Sistema Fretes no Cursor
=========================================

Script para inicializar rapidamente o ambiente de desenvolvimento.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description):
    """Executa comando e mostra resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - OK")
            return True
        else:
            print(f"❌ {description} - ERRO: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERRO: {e}")
        return False

def main():
    print("🚀 QUICK START - SISTEMA FRETES")
    print("=" * 40)
    
    # 1. Verificar sistema
    run_command("python app/claude_ai_novo/check_status.py", "Verificando sistema")
    
    # 2. Instalar dependências se necessário
    if not Path("venv").exists():
        print("📦 Criando virtual environment...")
        run_command("python -m venv venv", "Criando venv")
    
    # 3. Validar sistema
    run_command("python app/claude_ai_novo/validador_sistema_real.py", "Validando sistema completo")
    
    print("\\n✅ Quick Start concluído!")
    print("\\n📋 Próximos passos:")
    print("1. Abrir Cursor no workspace: frete_sistema.code-workspace")
    print("2. Usar Task: 🚀 Start Flask Development")
    print("3. Testar APIs: api_tests.http")
    print("4. Monitor: python app/claude_ai_novo/monitoring/cursor_monitor.py")

if __name__ == "__main__":
    main()
'''
            
            quick_start_file = self.project_root / "quick_start.py"
            with open(quick_start_file, 'w', encoding='utf-8') as f:
                f.write(quick_start_content)
            
            print("✅ Script quick_start.py criado")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar quick start: {e}")
            return False
    
    def run_setup(self) -> bool:
        """Executa setup completo"""
        steps = [
            ("Configurações VSCode", self.create_vscode_settings),
            ("Configurações de Debug", self.create_launch_config),
            ("Tasks do Cursor", self.create_tasks_config),
            ("Extensões Recomendadas", self.create_extensions_config),
            ("Diretório Monitoring", self.create_monitor_directory),
            ("Verificação de Arquivos", self.verify_files_exist),
            ("Ambiente Python", self.test_python_environment),
            ("Script Quick Start", self.create_quick_start_script)
        ]
        
        print("\\n🔧 Executando setup...")
        print("-" * 30)
        
        for step_name, step_func in steps:
            print(f"\\n📋 {step_name}:")
            if step_func():
                self.success_count += 1
            time.sleep(0.5)  # Pausa visual
        
        return self.success_count == self.total_steps
    
    def show_final_report(self):
        """Mostra relatório final"""
        print("\\n" + "=" * 60)
        print("📊 RELATÓRIO FINAL")
        print("=" * 60)
        print(f"✅ Passos concluídos: {self.success_count}/{self.total_steps}")
        
        success_rate = (self.success_count / self.total_steps) * 100
        
        if success_rate == 100:
            status = "🎉 SETUP COMPLETO!"
            color = "verde"
        elif success_rate >= 80:
            status = "⚠️ SETUP PARCIAL"
            color = "amarelo"
        else:
            status = "❌ SETUP COM PROBLEMAS"
            color = "vermelho"
        
        print(f"📈 Taxa de sucesso: {success_rate:.1f}%")
        print(f"🎯 Status: {status}")
        
        print("\\n🚀 PRÓXIMOS PASSOS:")
        print("1. Abrir Cursor")
        print("2. File > Open Workspace > frete_sistema.code-workspace")
        print("3. Instalar extensões recomendadas")
        print("4. Ctrl+Shift+P > Tasks > 🚀 Start Flask Development")
        print("5. Testar APIs com api_tests.http")
        
        print("\\n💡 COMANDOS ÚTEIS:")
        print("• python quick_start.py - Setup rápido")
        print("• python app/claude_ai_novo/check_status.py - Status")
        print("• python app/claude_ai_novo/monitoring/cursor_monitor.py - Monitor")
        
        print("\\n📚 DOCUMENTAÇÃO:")
        print("• .cursorrules - Regras do Cursor")
        print("• GUIA_CONFIGURACAO_CURSOR.md - Guia detalhado") 
        print("• api_tests.http - Testes de API")

def main():
    """Função principal"""
    try:
        setup = CursorSetup()
        
        if setup.run_setup():
            setup.show_final_report()
        else:
            print("\\n⚠️ Setup completado com alguns problemas.")
            print("Verifique os erros acima e tente novamente.")
            setup.show_final_report()
            
    except KeyboardInterrupt:
        print("\\n🛑 Setup interrompido pelo usuário.")
    except Exception as e:
        print(f"\\n❌ Erro fatal no setup: {e}")

if __name__ == "__main__":
    main() 