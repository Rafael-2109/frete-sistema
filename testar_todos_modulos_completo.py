#!/usr/bin/env python3
"""
🧪 TESTE COMPLETO DE MÓDULOS - Claude AI Novo
=============================================

Testa todos os módulos do sistema Claude AI Novo para verificar:
- Imports funcionando
- Classes instanciáveis  
- Métodos principais disponíveis
- Compatibilidade entre componentes

Versão: 2.0 - Com PYTHONPATH corrigido para resolver imports de app
"""

import sys
import os
from pathlib import Path

# 🔧 CORREÇÃO CRÍTICA: Configurar PYTHONPATH para encontrar módulo 'app'
current_dir = Path(__file__).parent
app_dir = current_dir.parent  # Vai para app/
root_dir = app_dir.parent     # Vai para raiz do projeto

# Adicionar caminhos necessários ao PYTHONPATH
for path in [str(root_dir), str(app_dir), str(current_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"🔧 PYTHONPATH configurado:")
print(f"   📂 Raiz: {root_dir}")
print(f"   📂 App: {app_dir}")
print(f"   📂 Claude AI Novo: {current_dir}")
print(f"✅ Módulo 'app' deve estar acessível agora\n")

import importlib
import traceback
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# ... resto do código ... 