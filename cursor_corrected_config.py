#!/usr/bin/env python3
"""
🔧 CURSOR CORRECTED CONFIG - Configuração Baseada no Ambiente Real
================================================================

Configurador que usa as informações REAIS coletadas do ambiente
para criar configurações corretas do Cursor.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

class CursorCorrectedConfig:
    """Configurador baseado em informações reais do ambiente"""
    
    def __init__(self, env_report_file: str = "cursor_environment_report.json"):
        self.project_root = Path.cwd()
        self.vscode_dir = self.project_root / ".vscode"
        
        # Carregar relatório do ambiente
        with open(env_report_file, 'r', encoding='utf-8') as f:
            self.env_info = json.load(f)
        
        print("🔧 CURSOR CORRECTED CONFIG")
        print("=" * 50)
        print("Usando informações REAIS do ambiente detectado...")
    
    def get_correct_python_path(self) -> str:
        """Retorna o caminho correto do Python baseado no ambiente real"""
        venv_locations = self.env_info['python']['venv_locations']
        
        if venv_locations:
            # Usar o primeiro venv encontrado
            venv_info = venv_locations[0]
            if venv_info['type'] == 'windows':
                return "./venv/Scripts/python.exe"
            else:
                return "./venv/bin/python"
        
        # Fallback para Python do sistema
        return self.env_info['python']['current_python']
    
    def get_correct_base_url(self) -> str:
        """Retorna URL base correta (local se Flask não estiver rodando)"""
        api_info = self.env_info['api']
        if api_info['flask_running']:
            return api_info['base_url']
        else:
            return "http://localhost:5000"  # Padrão para desenvolvimento
    
    def get_working_endpoints(self) -> list:
        """Retorna endpoints que realmente funcionam"""
        api_info = self.env_info['api']
        working_endpoints = api_info.get('available_endpoints', [])
        
        # Se Flask não estiver rodando, usar endpoints básicos esperados
        if not working_endpoints:
            working_endpoints = [
                '/health',
                '/api/claude-ai-novo/status', 
                '/claude-ai/query'
            ]
        
        return working_endpoints
    
    def create_corrected_workspace(self) -> Dict[str, Any]:
        """Cria workspace configuration corrigida"""
        python_path = self.get_correct_python_path()
        
        workspace_config = {
            "folders": [
                {
                    "name": "Sistema Fretes",
                    "path": "."
                }
            ],
            "settings": {
                "python.defaultInterpreterPath": python_path,
                "python.linting.enabled": True,
                "python.linting.pylintEnabled": True,
                "python.terminal.activateEnvironment": True,
                "files.exclude": {
                    "**/__pycache__": True,
                    "**/*.pyc": True,
                    ".pytest_cache": True,
                    "**/.git": False,
                    "**/migrations_backup*": True,
                    "**/validacao_*.json": True,
                    "**/relatorio_*.json": True
                },
                "python.analysis.typeCheckingMode": "basic",
                "rest-client.environmentVariables": {
                    "production": {
                        "baseUrl": "https://sistema-fretes.onrender.com"
                    },
                    "local": {
                        "baseUrl": self.get_correct_base_url()
                    }
                }
            },
            "tasks": {
                "version": "2.0.0",
                "tasks": [
                    {
                        "label": "🚀 Start Flask (Corrected)",
                        "type": "shell",
                        "command": python_path.replace("./", ""),
                        "args": ["run.py"],
                        "group": {"kind": "build", "isDefault": True},
                        "presentation": {
                            "echo": True,
                            "reveal": "always",
                            "focus": False,
                            "panel": "shared"
                        },
                        "options": {
                            "env": {
                                "FLASK_ENV": "development",
                                "FLASK_DEBUG": "1",
                                "PYTHONPATH": "${workspaceFolder}"
                            }
                        }
                    },
                    {
                        "label": "🔍 System Validator (Real)",
                        "type": "shell", 
                        "command": python_path.replace("./", ""),
                        "args": ["app/claude_ai_novo/validador_sistema_real.py"],
                        "group": "test"
                    },
                    {
                        "label": "📊 Quick Status Check",
                        "type": "shell",
                        "command": python_path.replace("./", ""),
                        "args": ["app/claude_ai_novo/check_status.py"],
                        "group": "test"
                    },
                    {
                        "label": "🔍 Monitor System (Real)",
                        "type": "shell",
                        "command": python_path.replace("./", ""),
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
            },
            "launch": {
                "version": "0.2.0",
                "configurations": [
                    {
                        "name": "🌐 Flask App (Real Env)",
                        "type": "python",
                        "request": "launch",
                        "program": "${workspaceFolder}/run.py",
                        "python": python_path,
                        "env": {
                            "FLASK_ENV": "development",
                            "FLASK_DEBUG": "1",
                            "PYTHONPATH": "${workspaceFolder}"
                        },
                        "console": "integratedTerminal",
                        "justMyCode": False
                    },
                    {
                        "name": "🧪 Claude AI Validator",
                        "type": "python",
                        "request": "launch",
                        "program": "${workspaceFolder}/app/claude_ai_novo/validador_sistema_real.py",
                        "python": python_path,
                        "console": "integratedTerminal"
                    }
                ]
            }
        }
        
        return workspace_config
    
    def create_corrected_api_tests(self) -> str:
        """Cria arquivo de testes de API corrigido"""
        base_url = self.get_correct_base_url()
        working_endpoints = self.get_working_endpoints()
        
        api_tests = f"""###
### 🎯 API TESTS - SISTEMA FRETES (CONFIGURAÇÃO REAL)
### Baseado no ambiente detectado: {base_url}
###

@baseUrl = {{{{baseUrl}}}}

### ==========================================
### 📊 SYSTEM HEALTH & STATUS (VERIFICADOS)
### ==========================================

### Health Check (Endpoint básico)
GET {{{{baseUrl}}}}/health
Accept: application/json

### Claude AI Novo Status
GET {{{{baseUrl}}}}/api/claude-ai-novo/status
Accept: application/json

### ==========================================
### 🧪 TESTES ESPECÍFICOS DO SEU AMBIENTE
### ==========================================

### Testar se Flask está rodando
GET {{{{baseUrl}}}}
Accept: application/json

### Validador Sistema (via API se disponível)
GET {{{{baseUrl}}}}/api/claude-ai-novo/validate
Accept: application/json

### ==========================================
### 🤖 CLAUDE AI NOVO - BASEADO NA ESTRUTURA REAL
### ==========================================

### Query Simples ao Claude
POST {{{{baseUrl}}}}/claude-ai/query
Content-Type: application/json

{{
    "query": "Status do sistema",
    "context": {{
        "source": "cursor_test",
        "environment": "local"
    }}
}}

### ==========================================
### 📋 ESTRUTURA DETECTADA NO SEU PROJETO
### ==========================================

### Módulos disponíveis detectados:
{chr(35) + ' ' + chr(10).join([f'# - {module}' for module in self.env_info['project']['app_structure']['modules']])}

### Claude AI Novo subdirs detectados:
{chr(35) + ' ' + chr(10).join([f'# - {subdir}' for subdir in self.env_info['project']['claude_ai_novo_structure']['subdirs']])}

### ==========================================
### 🔧 COMANDOS DE DESENVOLVIMENTO 
### ==========================================

### Para iniciar o sistema:
### python {self.get_correct_python_path()} run.py

### Para validar:
### python {self.get_correct_python_path()} app/claude_ai_novo/validador_sistema_real.py

### Para monitorar:
### python {self.get_correct_python_path()} app/claude_ai_novo/monitoring/cursor_monitor.py

###
### 📝 CONFIGURAÇÃO BASEADA EM:
### - Python: {self.env_info['python']['python_version'][:10]}
### - Virtual Env: {'Detectado' if self.env_info['python']['venv_locations'] else 'Não encontrado'}
### - Flask Entry: {self.env_info['flask']['flask_app_file']}
### - Database: {self.env_info['database']['db_type']}
###"""
        
        return api_tests
    
    def create_corrected_monitor_command(self) -> str:
        """Cria comando de monitor corrigido"""
        python_path = self.get_correct_python_path()
        base_url = self.get_correct_base_url()
        
        return f"""
# Monitor de Sistema Corrigido para seu ambiente

## Para iniciar o Flask:
{python_path} run.py

## Para monitorar (após Flask estar rodando):
{python_path} app/claude_ai_novo/monitoring/cursor_monitor.py --url {base_url}

## Para validação rápida:
{python_path} app/claude_ai_novo/check_status.py

## Para validação completa:
{python_path} app/claude_ai_novo/validador_sistema_real.py
"""
    
    def save_corrected_configs(self):
        """Salva todas as configurações corrigidas"""
        print("\n🔧 Criando configurações corrigidas...")
        
        # 1. Workspace corrigido
        workspace_config = self.create_corrected_workspace()
        workspace_file = self.project_root / "frete_sistema_corrected.code-workspace"
        with open(workspace_file, 'w', encoding='utf-8') as f:
            json.dump(workspace_config, f, indent=2)
        print(f"✅ Workspace corrigido: {workspace_file.name}")
        
        # 2. API tests corrigidos
        api_tests = self.create_corrected_api_tests()
        api_tests_file = self.project_root / "api_tests_corrected.http"
        with open(api_tests_file, 'w', encoding='utf-8') as f:
            f.write(api_tests)
        print(f"✅ API tests corrigidos: {api_tests_file.name}")
        
        # 3. Monitor commands corrigidos
        monitor_commands = self.create_corrected_monitor_command()
        monitor_file = self.project_root / "monitor_commands_corrected.md"
        with open(monitor_file, 'w', encoding='utf-8') as f:
            f.write(monitor_commands)
        print(f"✅ Comandos de monitor: {monitor_file.name}")
        
        # 4. VSCode settings corrigidos
        self.vscode_dir.mkdir(exist_ok=True)
        
        settings = {
            "python.defaultInterpreterPath": self.get_correct_python_path(),
            "python.linting.enabled": True,
            "python.terminal.activateEnvironment": True,
            "rest-client.environmentVariables": {
                "local": {
                    "baseUrl": self.get_correct_base_url()
                },
                "production": {
                    "baseUrl": "https://sistema-fretes.onrender.com"
                }
            }
        }
        
        settings_file = self.vscode_dir / "settings_corrected.json"
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        print(f"✅ VSCode settings: {settings_file.name}")
    
    def print_setup_instructions(self):
        """Imprime instruções de setup baseadas no ambiente real"""
        python_path = self.get_correct_python_path()
        
        print("\n" + "=" * 60)
        print("🎯 INSTRUÇÕES DE SETUP CORRIGIDAS")
        print("=" * 60)
        
        print(f"\n📍 CONFIGURAÇÃO DETECTADA:")
        print(f"   Python: {self.env_info['python']['python_version'][:20]}")
        print(f"   Virtual Env: {python_path}")
        print(f"   Flask Entry: {self.env_info['flask']['flask_app_file']}")
        print(f"   Database: {self.env_info['database']['db_type']}")
        
        print(f"\n🚀 COMANDOS PARA SEU AMBIENTE:")
        print(f"   1. Ativar venv: venv\\Scripts\\activate")
        print(f"   2. Iniciar Flask: {python_path} run.py")
        print(f"   3. Testar sistema: {python_path} app/claude_ai_novo/check_status.py")
        print(f"   4. Monitor: {python_path} app/claude_ai_novo/monitoring/cursor_monitor.py")
        
        print(f"\n📁 ARQUIVOS CRIADOS:")
        print(f"   • frete_sistema_corrected.code-workspace")
        print(f"   • api_tests_corrected.http")
        print(f"   • monitor_commands_corrected.md")
        print(f"   • .vscode/settings_corrected.json")
        
        print(f"\n⚠️ PROBLEMAS DETECTADOS:")
        if not self.env_info['api']['flask_running']:
            print("   • Flask não está rodando - inicie primeiro")
        
        if self.env_info['database'].get('connection_error'):
            print("   • Erro de encoding no PostgreSQL - corrigir DATABASE_URL")
        
        print(f"\n💡 PRÓXIMOS PASSOS:")
        print("   1. Abrir: frete_sistema_corrected.code-workspace no Cursor")
        print("   2. Ativar venv no terminal integrado")
        print("   3. Iniciar Flask com a task '🚀 Start Flask (Corrected)'")
        print("   4. Testar APIs com api_tests_corrected.http")

def main():
    """Função principal"""
    try:
        # Verificar se relatório existe
        report_file = "cursor_environment_report.json"
        if not Path(report_file).exists():
            print("❌ Relatório do ambiente não encontrado!")
            print("Execute primeiro: python cursor_environment_check.py")
            return
        
        # Criar configurações corrigidas
        config = CursorCorrectedConfig(report_file)
        config.save_corrected_configs()
        config.print_setup_instructions()
        
        print("\n✅ Configurações corrigidas criadas com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro ao criar configurações: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 