#!/usr/bin/env python3
"""
QueryAnalyzer - Análise especializada
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

class QueryAnalyzer:
    """Classe para análise especializada"""
    
    def __init__(self):
        pass
        
    def _analisar_consulta_profunda(self, consulta: str) -> Dict[str, Any]:
        """🧠 Análise profunda da consulta (similar ao Cursor)"""
        return {
            'tipo': 'dados' if any(palavra in consulta.lower() for palavra in ['entregas', 'fretes', 'pedidos']) else 'desenvolvimento',
            'complexidade': 'alta' if len(consulta.split()) > 10 else 'media',
            'contexto_necessario': True if any(palavra in consulta.lower() for palavra in ['cliente', 'período', 'comparar']) else False,
            'ferramentas_necessarias': ['database', 'excel'] if 'excel' in consulta.lower() else ['database'],
            'confianca_interpretacao': 0.9 if len(consulta.split()) > 3 else 0.6
        }
    def _analisar_consulta(self, consulta: str) -> Dict[str, Any]:
        """Análise simplificada da consulta para dar mais liberdade ao Claude"""
        
        analise = {
            "tipo_consulta": "aberta",  # Deixar o Claude decidir
            "consulta_original": consulta,
            "periodo_dias": 30,  # Padrão
            "cliente_especifico": None,
            "dominio": "geral",
            "foco_dados": [],
            "metricas_solicitadas": [],
            "requer_dados_completos": False,
            "multi_dominio": False,
            "dominios_solicitados": []
        }
        
        consulta_lower = consulta.lower()
        
        # Detecção básica de período temporal (manter isso porque é útil)
        import re
        
        # Detectar dias específicos
        dias_match = re.search(r'(\d+)\s*dias?', consulta_lower)
        if dias_match:
            analise["periodo_dias"] = int(dias_match.group(1))
        elif "semana" in consulta_lower:
            analise["periodo_dias"] = 7
        elif "mês" in consulta_lower or "mes" in consulta_lower:
            analise["periodo_dias"] = 30
        
        # Detecção básica de cliente (deixar mais flexível)
        from app.utils.grupo_empresarial import GrupoEmpresarialDetector
        detector_grupos = GrupoEmpresarialDetector()
        grupo_detectado = detector_grupos.detectar_grupo_na_consulta(consulta)
        
        if grupo_detectado:
            analise["cliente_especifico"] = grupo_detectado['grupo_detectado']
            analise["filtro_sql"] = grupo_detectado.get('filtro_sql')
            analise["grupo_empresarial"] = grupo_detectado
            logger.info(f"🏢 Cliente detectado: {grupo_detectado['grupo_detectado']}")
        
        # Deixar o Claude interpretar livremente o domínio e intenção
        # Apenas marcar algumas palavras-chave básicas para ajudar
        palavras_encontradas = []
        
        palavras_chave = {
            "entregas": ["entrega", "entregue", "atraso", "prazo", "pendente"],
            "pedidos": ["pedido", "cotar", "cotação"],
            "faturamento": ["faturou", "faturamento", "receita", "vendas", "valor total"],
            "embarques": ["embarque", "embarcado", "separação"],
            "fretes": ["frete", "cte", "transportadora"],
            "clientes": ["cliente", "clientes"]
        }
        
        for dominio, palavras in palavras_chave.items():
            for palavra in palavras:
                if palavra in consulta_lower:
                    palavras_encontradas.append(palavra)
                    if dominio not in analise["foco_dados"]:
                        analise["foco_dados"].append(dominio)
        
        # Log simplificado
        logger.info(f"📊 Análise simplificada: período={analise['periodo_dias']}d, cliente={analise['cliente_especifico'] or 'todos'}")
        if palavras_encontradas:
            logger.info(f"🔍 Palavras-chave: {', '.join(palavras_encontradas[:5])}")
        
        return analise

# Instância global
_queryanalyzer = None

def get_queryanalyzer():
    """Retorna instância de QueryAnalyzer"""
    global _queryanalyzer
    if _queryanalyzer is None:
        _queryanalyzer = QueryAnalyzer()
    return _queryanalyzer
