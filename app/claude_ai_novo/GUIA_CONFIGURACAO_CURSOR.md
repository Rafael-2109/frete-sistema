# 🎯 GUIA: CONECTAR CURSOR AO SISTEMA FRETES

## 🔌 **OPÇÕES DE CONEXÃO DISPONÍVEIS**

### **1. 🌐 DESENVOLVIMENTO REMOTO (Render/Servidor)**

#### **A. SSH Connection (se disponível)**
```bash
# No Cursor: Ctrl+Shift+P > "Remote-SSH: Connect to Host"
# Adicionar host no config SSH

# ~/.ssh/config
Host render-fretes
    HostName your-app.onrender.com
    User app-user
    Port 22
    IdentityFile ~/.ssh/render_key
```

#### **B. API Testing Direto**
```json
// .vscode/settings.json (funciona no Cursor)
{
    "rest-client.environmentVariables": {
        "production": {
            "baseUrl": "https://sistema-fretes.onrender.com",
            "apiKey": "${API_KEY}"
        },
        "local": {
            "baseUrl": "http://localhost:5000",
            "apiKey": "dev-key"
        }
    }
}
```

### **2. 🏠 DESENVOLVIMENTO LOCAL INTEGRADO**

#### **A. Configuração do Workspace**
```json
// frete_sistema.code-workspace
{
    "folders": [
        {
            "name": "Sistema Fretes",
            "path": "."
        }
    ],
    "settings": {
        "python.defaultInterpreterPath": "./venv/bin/python",
        "python.linting.enabled": true,
        "python.linting.pylintEnabled": true,
        "files.exclude": {
            "**/__pycache__": true,
            "**/*.pyc": true,
            ".pytest_cache": true
        }
    },
    "extensions": {
        "recommendations": [
            "ms-python.python",
            "ms-python.debugpy",
            "humao.rest-client",
            "ms-vscode.vscode-json",
            "redhat.vscode-yaml"
        ]
    }
}
```

#### **B. Debugging Configurado**
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask App",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/run.py",
            "env": {
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1"
            },
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Claude AI Novo Tests",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/app/claude_ai_novo/validador_sistema_real.py",
            "console": "integratedTerminal"
        }
    ]
}
```

### **3. 🧪 TESTING INTEGRADO**

#### **A. Arquivo de Testes API (.http)**
```http
### Testar Claude AI Novo
POST {{baseUrl}}/claude-ai/query
Content-Type: application/json

{
    "query": "Quais pedidos estão pendentes?",
    "context": {
        "user_id": 1
    }
}

### Testar Validador Sistema
GET {{baseUrl}}/api/claude-ai-novo/status

### Testar Orchestrator
POST {{baseUrl}}/api/claude-ai-novo/process
Content-Type: application/json

{
    "type": "intelligent_query",
    "data": "Análise de fretes"
}
```

#### **B. Pytest Configuration**
```ini
# pytest.ini
[tool:pytest]
testpaths = app/claude_ai_novo/tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    api: marks tests as API tests
```

### **4. 🔍 MONITORING EM TEMPO REAL**

#### **A. Log Viewer Setup**
```python
# app/claude_ai_novo/monitoring/log_viewer.py
import asyncio
import websockets
import json
from pathlib import Path

class RealTimeLogViewer:
    """Visualizador de logs em tempo real para Cursor"""
    
    def __init__(self, log_file: str = "app.log"):
        self.log_file = Path(log_file)
        self.clients = set()
    
    async def tail_logs(self):
        """Monitora logs em tempo real"""
        with open(self.log_file, 'r') as f:
            f.seek(0, 2)  # Go to end
            while True:
                line = f.readline()
                if line:
                    await self.broadcast_log(line.strip())
                await asyncio.sleep(0.1)
    
    async def broadcast_log(self, log_line: str):
        """Envia log para todos os clientes conectados"""
        if self.clients:
            message = json.dumps({
                'type': 'log',
                'data': log_line,
                'timestamp': datetime.now().isoformat()
            })
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
```

#### **B. Task Configuration**
```json
// .vscode/tasks.json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Flask with Logging",
            "type": "shell",
            "command": "python",
            "args": ["run.py"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
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
            "label": "Run System Validator",
            "type": "shell",
            "command": "python",
            "args": ["app/claude_ai_novo/validador_sistema_real.py"],
            "group": "test"
        },
        {
            "label": "Watch Logs",
            "type": "shell",
            "command": "tail",
            "args": ["-f", "app.log"],
            "group": "build",
            "presentation": {
                "echo": false,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated"
            }
        }
    ]
}
```

### **5. 🎛️ CURSOR-ESPECÍFICO: COMPOSER INTEGRATION**

#### **A. Configurar Composer para Sistema**
```python
# cursor_integration.py
"""
Integração específica para Cursor Composer
Permite que o Composer entenda melhor o sistema
"""

def get_system_context():
    """Retorna contexto do sistema para Composer"""
    return {
        "type": "flask_application",
        "name": "Sistema de Fretes",
        "modules": [
            "claude_ai_novo",
            "fretes", 
            "pedidos",
            "embarques"
        ],
        "current_issues": [
            "UTF-8 encoding errors",
            "Claude AI API integration", 
            "Module import conflicts"
        ],
        "architecture": "microservices_orchestrated",
        "test_files": [
            "app/claude_ai_novo/validador_sistema_real.py",
            "app/claude_ai_novo/teste_correcoes_finais.py"
        ]
    }
```

#### **B. Cursor Rules Enhancement**
```markdown
<!-- .cursorrules -->
## Sistema Fretes Context

Este é um sistema Flask com arquitetura de orquestradores. 

### Estrutura Principal:
- `app/claude_ai_novo/` - Sistema de IA integrado
- `app/fretes/` - Gestão de fretes
- `app/pedidos/` - Gestão de pedidos

### Para testes, sempre usar:
```bash
python app/claude_ai_novo/validador_sistema_real.py
```

### Problemas conhecidos:
1. Encoding UTF-8 na conexão PostgreSQL
2. Imports circulares entre modules
3. Claude API key configuration

### Ao fazer alterações:
1. Rodar validador primeiro
2. Verificar logs de produção
3. Testar imports não quebram
```

## 🚀 **SETUP RECOMENDADO PARA SEU CASO**

### **OPÇÃO 1: 🎯 DESENVOLVIMENTO LOCAL OTIMIZADO**
```bash
# 1. Abrir Cursor no diretório do projeto
code /c/Users/rafael.nascimento/Desktop/Sistema\ Online/frete_sistema

# 2. Instalar extensões recomendadas
# - Python
# - REST Client  
# - Error Lens
# - GitLens

# 3. Configurar Python Interpreter
# Ctrl+Shift+P > "Python: Select Interpreter"
```

### **OPÇÃO 2: 🌐 HYBRID DEVELOPMENT**
```bash
# Local development + Remote API testing
# 1. Código local no Cursor
# 2. Testes diretos na API de produção
# 3. Logs em tempo real via WebSocket/SSH
```

### **OPÇÃO 3: 🔄 CONTINUOUS SYNC**
```python
# Script para sincronizar mudanças
# sync_to_production.py
import os
import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ProductionSyncHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            # Sync específico para production
            self.deploy_changes(event.src_path)
```

## 💡 **PRÓXIMOS PASSOS RECOMENDADOS**

1. **Configure workspace local completo**
2. **Setup debugging integrado** 
3. **Crie arquivo .http para API testing**
4. **Configure monitoring em tempo real**
5. **Use validador sistema como health check**

Quer que eu configure alguma dessas opções específicas para seu ambiente? 