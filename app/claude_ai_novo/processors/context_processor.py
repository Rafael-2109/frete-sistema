#!/usr/bin/env python3
"""
ContextProcessor - Processamento especializado
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

# Configurar logger
logger = logging.getLogger(__name__)

class ContextProcessor:
    """Classe para processamento especializado"""
    
    def __init__(self):
        pass
        
    def _build_contexto_por_intencao(self, intencoes_scores: Dict[str, float], 
                                      analise: Dict[str, Any]) -> str:
        """
        Constrói contexto específico baseado na intenção dominante
        """
        # Encontrar intenção dominante
        intencao_principal = max(intencoes_scores, key=lambda k: intencoes_scores[k])
        score_principal = intencoes_scores[intencao_principal]
        
        # Log da intenção detectada
        logger.info(f"🎯 Intenção principal: {intencao_principal} ({score_principal:.1%})")
        
        # Se confiança baixa, usar contexto genérico
        if score_principal < 0.4:
            return self._descrever_contexto_carregado(analise)
        
        # Contextos específicos por intenção
        periodo = analise.get('periodo_dias', 30)
        cliente = analise.get('cliente_especifico')
        
        if intencao_principal == "desenvolvimento":
            return """Contexto: Sistema Flask/PostgreSQL
Estrutura: app/[modulo]/{models,routes,forms}.py  
Padrões: SQLAlchemy, WTForms, Jinja2
Módulos: pedidos, fretes, embarques, monitoramento, separacao, carteira, etc."""
        
        elif intencao_principal == "analise_dados":
            registros = self._ultimo_contexto_carregado.get('registros_carregados', 0) if hasattr(self, '_ultimo_contexto_carregado') else 0
            base = f"Dados: {registros} registros, {periodo} dias"
            if cliente:
                base += f", cliente: {cliente}"
            return base
        
        elif intencao_principal == "resolucao_problema":
            return "Contexto: Diagnóstico e resolução\nSistema: Flask/PostgreSQL\nLogs disponíveis"
        
        elif intencao_principal == "comando_acao":
            return f"Ação solicitada. Período: {periodo} dias" + (f", Cliente: {cliente}" if cliente else "")
        
        else:
            return self._descrever_contexto_carregado(analise)
    def _descrever_contexto_carregado(self, analise: Dict[str, Any]) -> str:
        """Descrição simplificada do contexto para o Claude"""
        if not hasattr(self, '_ultimo_contexto_carregado') or not self._ultimo_contexto_carregado:
            return ""
        
        dados = self._ultimo_contexto_carregado.get('dados_especificos', {})
        if not dados:
            return ""
        
        # Contexto básico
        periodo = analise.get('periodo_dias', 30)
        cliente = analise.get('cliente_especifico')
        
        if cliente:
            return f"Contexto: {cliente}, últimos {periodo} dias."
        else:
            return f"Contexto: últimos {periodo} dias."

# Instância global
_contextprocessor = None

def get_contextprocessor():
    """Retorna instância de ContextProcessor"""
    global _contextprocessor
    if _contextprocessor is None:
        _contextprocessor = ContextProcessor()
    return _contextprocessor
