#!/usr/bin/env python3
"""
ResponseUtils - Utilitários especializados
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
from app.fretes.models import DespesaExtra
from app.financeiro.models import PendenciaFinanceiraNF

class ResponseUtils:
    """Classe para utilitários especializados"""
    
    def __init__(self):
        pass
        
    def _formatar_resultado_cursor(self, resultado: Dict[str, Any], titulo: str) -> str:
        """Formata resultado do Cursor Mode"""
        if 'error' in resultado:
            return f"❌ **Erro em {titulo}:** {resultado['error']}"
        
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        if titulo == 'Análise de Código':
            return f"""🔍 **{titulo} Completa**

📊 **Visão Geral:**
{self._formatar_analise_projeto(resultado)}

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode + Claude Development AI"""
        
        elif titulo == 'Geração de Código':
            if resultado.get('status') == 'success':
                return f"""🚀 **{titulo} - Sucesso!**

📦 **Módulo:** {resultado.get('module_name', 'N/A')}
📁 **Arquivos Criados:** {resultado.get('total_files', 0)} arquivos
📋 **Lista de Arquivos:**
{chr(10).join(f"• {arquivo}" for arquivo in resultado.get('files_created', []))}

📚 **Documentação Gerada:**
{resultado.get('documentation', 'Documentação automática criada')}

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode + Code Generator"""
            else:
                return f"❌ **Erro na {titulo}:** {resultado.get('error', 'Erro desconhecido')}"
        
        else:
            # Formato genérico
            return f"""✅ **{titulo} Concluído**

📋 **Resultado:** {str(resultado)[:500]}...

---
🎯 **Processado:** {timestamp}
⚡ **Fonte:** Cursor Mode"""
    def _formatar_analise_projeto(self, analise: Dict[str, Any]) -> str:
        """Formata análise do projeto"""
        overview = analise.get('project_overview', {})
        issues = analise.get('potential_issues', [])
        
        return f"""• **Módulos:** {overview.get('total_modules', 0)}
• **Modelos:** {overview.get('total_models', 0)}
• **Rotas:** {overview.get('total_routes', 0)}
• **Templates:** {overview.get('total_templates', 0)}
• **Problemas Detectados:** {len(issues)}
• **Arquitetura:** {overview.get('architecture_pattern', 'Flask MVC')}"""
    def _formatar_status_cursor(self, status: Dict[str, Any]) -> str:
        """Formata status do Cursor Mode"""
        return f"""📊 **Status do Cursor Mode**

🔧 **Estado:** {'✅ Ativo' if status['activated'] else '❌ Inativo'}

⚙️ **Funcionalidades:**
{chr(10).join(f"• {feature}: {'✅' if enabled else '❌'}" for feature, enabled in status['features'].items())}

🛠️ **Ferramentas:**
{chr(10).join(f"• {tool}: {'✅' if available else '❌'}" for tool, available in status['tools_available'].items())}

📋 **Capacidades Ativas:**
{chr(10).join(f"• {cap}" for cap in status.get('capabilities', []))}

---
🎯 **Cursor Mode - Sistema similar ao Cursor integrado!**"""

# Funções auxiliares para formatação de respostas
    def _gerar_resposta_erro(self, mensagem: str) -> Optional[Dict[str, Any]]:
        """Gera resposta de erro formatada"""
        return {
        'success': False,
        'error': mensagem,
        'response': f"❌ **Erro:** {mensagem}",
        'status': 'error'
    }
    def _gerar_resposta_sucesso(self, resposta: str) -> Optional[Dict[str, Any]]:
        """Gera resposta de sucesso formatada"""
        return {
        'success': True,
        'response': resposta,
        'status': 'success'
    }

# Adicionar nova função de detecção de consultas de desenvolvimento

# Instância global
_responseutils = None

def get_responseutils():
    """Retorna instância de ResponseUtils"""
    global _responseutils
    if _responseutils is None:
        _responseutils = ResponseUtils()
    return _responseutils
