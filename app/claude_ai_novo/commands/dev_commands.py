#!/usr/bin/env python3
"""
DevCommands - Comandos especializados
"""

import os
import anthropic
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from flask_login import current_user
from sqlalchemy import func, and_, or_, text
from app import db
import json
from app.utils.redis_cache import redis_cache, cache_aside, cached_query
from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
from app.utils.ml_models_real import get_ml_models_system
import config_ai
from app.utils.api_helper import get_system_alerts
from app.utils.ai_logging import ai_logger, AILogger
from app.utils.redis_cache import intelligent_cache
import re
import time
import asyncio

# Configurar logger
logger = logging.getLogger(__name__)
import re
from app.utils.grupo_empresarial import GrupoEmpresarialDetector
from app import db
from app.fretes.models import Frete
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from app.pedidos.models import Pedido
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.faturamento.models import RelatorioFaturamentoImportado
from app import db
from app.monitoramento.models import EntregaMonitorada
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app import db
from app.monitoramento.models import AgendamentoEntrega
from app import db
from app.monitoramento.models import EntregaMonitorada
from app.fretes.models import Frete
from app.utils.grupo_empresarial import detectar_grupo_empresarial
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import re
from app import db
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.embarques.models import Embarque, EmbarqueItem
from app.pedidos.models import Pedido
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.pedidos.models import Pedido
from app.utils.grupo_empresarial import GrupoEmpresarialDetector
import re
import re
import re
import re
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app import db
from app.transportadoras.models import Transportadora
from app.fretes.models import Frete
from app import db
from app.pedidos.models import Pedido
from app import db
from app.embarques.models import Embarque, EmbarqueItem
from datetime import date
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado as RelatorioImportado
from app import db
# from app.financeiro.models import PendenciaFinanceiraNF  # Comentado temporariamente

class DevCommands:
    """Classe para comandos especializados"""
    
    def __init__(self, claude_client=None):
        self.client = claude_client
        self.system_prompt = "Você é um assistente especializado em desenvolvimento Flask, Python, SQLAlchemy, WTForms, Jinja2, Bootstrap, HTML, CSS, JavaScript, React, Node.js, Express, MongoDB, PostgreSQL, MySQL, SQLite, Oracle, SQL Server, MariaDB, etc."
        
    def _is_dev_command(self, consulta: str) -> bool:
        """Detecta comandos de desenvolvimento/criação de código"""
        comandos_dev = [
            # Comandos diretos
            'criar módulo', 'crie módulo', 'criar modulo', 'crie modulo',
            'criar funcionalidade', 'criar função', 'criar rota',
            'criar modelo', 'criar model', 'criar tabela',
            'criar template', 'criar formulário', 'criar form',
            'desenvolver', 'programar', 'codificar', 'implementar',
            
            # Solicitações de código
            'código para', 'codigo para', 'script para',
            'função que', 'funcao que', 'método para',
            'classe para', 'api para', 'endpoint para',
            
            # Melhorias e otimizações
            'melhorar código', 'otimizar função', 'refatorar',
            'corrigir bug', 'resolver erro', 'debug',
            
            # Arquitetura
            'estrutura para', 'arquitetura de', 'design pattern',
            'organizar módulo', 'reestruturar'
        ]
        
        consulta_lower = consulta.lower()
        return any(comando in consulta_lower for comando in comandos_dev)
    def _processar_comando_desenvolvimento(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa comandos de desenvolvimento com contexto do projeto"""
        logger.info(f"💻 Processando comando de desenvolvimento: {consulta[:50]}...")
        
        # Adicionar contexto específico do projeto
        contexto_projeto = """
        
**ESTRUTURA DO PROJETO**:
```
app/
├── [módulo]/
│   ├── __init__.py      # Blueprint e inicialização
│   ├── models.py        # Modelos SQLAlchemy
│   ├── routes.py        # Rotas Flask
│   ├── forms.py         # Formulários WTForms
├── templates/           # Templates HTML
├── utils/               # Utilitários compartilhados
├── static/              # CSS, JS, imagens
```

**PADRÕES DO SISTEMA**:
- Modelos: SQLAlchemy com db.Model
- Formulários: WTForms com FlaskForm
- Templates: Jinja2 com herança de base.html
- Autenticação: @login_required
- Permissões: @require_financeiro(), @require_admin()
- Logs: logger.info(), logger.error()
"""
        
        # Processar com Claude incluindo contexto
        messages = [
            {
                "role": "user",
                "content": consulta + contexto_projeto
            }
        ]
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                temperature=0.5,  # Equilibrio entre determinismo e criatividade
                timeout=120.0,
                system=self.system_prompt,
                messages=messages  # type: ignore
            )
            
            resultado = response.content[0].text
            
            # Adicionar rodapé
            return f"""{resultado}

---
💻 **Desenvolvimento com Claude 4 Sonnet**
🔧 Sistema Flask + PostgreSQL
🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
            
        except Exception as e:
            logger.error(f"❌ Erro no comando de desenvolvimento: {e}")
            return f"""❌ **Erro ao processar comando de desenvolvimento**

Erro: {e}

Tente novamente ou consulte os logs para mais detalhes."""

# Instância global
_devcommands = None

def get_devcommands():
    """Retorna instância de DevCommands"""
    global _devcommands
    if _devcommands is None:
        _devcommands = DevCommands()
    return _devcommands
