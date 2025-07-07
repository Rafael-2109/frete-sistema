#!/usr/bin/env python3
"""
CursorCommands - Comandos especializados
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
from app.financeiro.models import PendenciaFinanceiraNF  # Comentado temporariamente

# Configurar logger
logger = logging.getLogger(__name__)

class CursorCommands:
    """Classe para comandos especializados"""
    
    def __init__(self, claude_client=None):
        self.client = claude_client
        
    def _is_cursor_command(self, consulta: str) -> bool:
        """🎯 Detecta comandos do Cursor Mode"""
        comandos_cursor = [
            'ativar cursor', 'cursor mode', 'modo cursor', 'ativa cursor',
            'analisar código', 'gerar código', 'modificar código', 'buscar código',
            'corrigir bugs', 'refatorar', 'documentar código', 'validar código',
            'cursor chat', 'chat código', 'ajuda código'
        ]
        
        consulta_lower = consulta.lower()
        return any(comando in consulta_lower for comando in comandos_cursor)
    def _processar_comando_cursor(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """🎯 Processa comandos do Cursor Mode"""
        try:
            from .cursor_mode import get_cursor_mode
            
            logger.info(f"🎯 Processando comando Cursor Mode: {consulta}")
            
            cursor = get_cursor_mode()
            consulta_lower = consulta.lower()
            
            # Comando de ativação
            if any(termo in consulta_lower for termo in ['ativar cursor', 'cursor mode', 'modo cursor', 'ativa cursor']):
                unlimited = 'ilimitado' in consulta_lower or 'unlimited' in consulta_lower
                resultado = cursor.activate_cursor_mode(unlimited)
                
                if resultado['status'] == 'success':
                    return f"""🎯 **CURSOR MODE ATIVADO COM SUCESSO!**

📊 **STATUS DA ATIVAÇÃO:**
• **Modo:** {resultado['mode']}
• **Ativado em:** {resultado['activated_at']}
• **Modo Ilimitado:** {'✅ Sim' if unlimited else '❌ Não'}

🔧 **FERRAMENTAS DISPONÍVEIS:**
{chr(10).join(f"• {cap}" for cap in resultado['capabilities'])}

📈 **ANÁLISE INICIAL DO PROJETO:**
• **Total de Módulos:** {resultado['initial_project_analysis']['total_modules']}
• **Total de Arquivos:** {resultado['initial_project_analysis']['total_files']}
• **Problemas Detectados:** {resultado['initial_project_analysis']['issues_detected']}

💡 **COMANDOS DISPONÍVEIS:**
• `analisar código` - Análise completa do projeto
• `gerar código [descrição]` - Geração automática
• `modificar código [arquivo]` - Modificação inteligente
• `buscar código [termo]` - Busca semântica
• `corrigir bugs` - Detecção e correção automática
• `cursor chat [mensagem]` - Chat com código

---
🎯 **Cursor Mode ativo! Agora tenho capacidades similares ao Cursor!**
⚡ **Fonte:** Claude 4 Sonnet + Development AI + Project Scanner"""
                else:
                    return f"❌ **Erro ao ativar Cursor Mode:** {resultado.get('error', 'Erro desconhecido')}"
            
            # Verificar se Cursor Mode está ativo
            if not cursor.activated:
                return """⚠️ **Cursor Mode não está ativo!**

💡 **Para ativar use:** `ativar cursor` ou `cursor mode`"""
            
            # Outros comandos...
            return "🎯 Cursor Mode processado com sucesso!"
            
        except Exception as e:
            return f"❌ Erro no comando Cursor: {e}"

# Instância global
_cursorcommands = None

def get_cursorcommands():
    """Retorna instância de CursorCommands"""
    global _cursorcommands
    if _cursorcommands is None:
        _cursorcommands = CursorCommands()
    return _cursorcommands
