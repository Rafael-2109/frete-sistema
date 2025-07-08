#!/usr/bin/env python3
"""
IntentionAnalyzer - Análise especializada
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
from app.utils.ai_logging import logger

# Configurar logger
logger = logging.getLogger(__name__)

class IntentionAnalyzer:
    """Classe para análise especializada"""
    
    def __init__(self):
        pass
    
    def analyze_intention(self, query: str) -> Dict[str, Any]:
        """Analisa a intenção do usuário na consulta"""
        intencoes = self._detectar_intencao_refinada(query)
        
        # Determinar intenção principal
        intencao_principal = max(intencoes, key=intencoes.get) if intencoes else "analise_dados"
        confianca = max(intencoes.values()) if intencoes else 0.5
        
        # Determinar se deve usar sistema avançado
        usar_avancado = self._deve_usar_sistema_avancado(query, intencoes)
        
        return {
            'intention': intencao_principal,
            'confidence': confianca,
            'all_intentions': intencoes,
            'use_advanced': usar_avancado,
            'query_length': len(query.split()),
            'complexity': 'high' if len(query.split()) > 15 else 'medium' if len(query.split()) > 8 else 'low'
        }
        
    def _detectar_intencao_refinada(self, consulta: str) -> Dict[str, float]:
        """
        Detecta múltiplas intenções com scores de confiança
        Retorna dict com probabilidades ao invés de categoria única
        """
        consulta_lower = consulta.lower()
        
        intencoes_scores = {
            "analise_dados": 0.0,
            "desenvolvimento": 0.0,
            "resolucao_problema": 0.0,
            "explicacao_conceitual": 0.0,
            "comando_acao": 0.0
        }
        
        # Palavras-chave com pesos
        padroes = {
            "analise_dados": {
                "palavras": ["quantos", "qual", "status", "relatório", "dados", "estatística", 
                           "total", "quantidade", "listar", "mostrar", "ver", "como", "quando"],
                "peso": 0.2
            },
            "desenvolvimento": {
                "palavras": ["criar", "desenvolver", "implementar", "código", "função", 
                           "módulo", "classe", "api", "rota", "template"],
                "peso": 0.25
            },
            "resolucao_problema": {
                "palavras": ["erro", "bug", "problema", "não funciona", "corrigir", 
                           "resolver", "falha", "exception", "debug"],
                "peso": 0.3
            },
            "explicacao_conceitual": {
                "palavras": ["como funciona", "o que é", "explique", "entender", 
                           "por que", "quando usar", "diferença entre"],
                "peso": 0.15
            },
            "comando_acao": {
                "palavras": ["gerar", "exportar", "executar", "fazer", "processar",
                           "excel", "relatório", "planilha", "baixar"],
                "peso": 0.2
            }
        }
        
        # Calcular scores
        for intencao, config in padroes.items():
            for palavra in config["palavras"]:
                if palavra in consulta_lower:
                    intencoes_scores[intencao] += config["peso"]
        
        # Normalizar scores
        total = sum(intencoes_scores.values())
        if total > 0:
            for intencao in intencoes_scores:
                intencoes_scores[intencao] /= total
        
        return intencoes_scores
    def _deve_usar_sistema_avancado(self, consulta: str, intencoes: Dict[str, float]) -> bool:
        """
        Decide logicamente se deve usar sistemas avançados
        Baseado em critérios objetivos, não apenas palavras-chave
        """
        # Critérios lógicos
        criterios = {
            "complexidade_alta": len(consulta.split()) > 20,
            "multiplas_intencoes": sum(1 for s in intencoes.values() if s > 0.2) >= 2,
            "solicitacao_explicita": any(termo in consulta.lower() for termo in 
                                       ["análise avançada", "análise profunda", "detalhada"]),
            "consulta_ambigua": max(intencoes.values()) < 0.4 if intencoes else False,
            "historico_contexto": hasattr(self, '_ultimo_contexto_carregado') and 
                                self._ultimo_contexto_carregado.get('registros_carregados', 0) > 1000
        }
        
        # Log para debug
        logger.debug(f"🔍 Critérios sistema avançado: {criterios}")
        
        # Decisão baseada em múltiplos fatores
        pontos = sum(1 for criterio, valor in criterios.items() if valor)
        
        # Caso especial: múltiplas intenções sempre usa avançado
        if criterios["multiplas_intencoes"]:
            usar_avancado = True
        else:
            usar_avancado = pontos >= 2  # Precisa de pelo menos 2 critérios verdadeiros
        
        if usar_avancado:
            logger.info(f"🚀 Sistema avançado ativado: {pontos} critérios atendidos")
        
        return usar_avancado

# Instância global
_intentionanalyzer = None

def get_intentionanalyzer():
    """Retorna instância de IntentionAnalyzer"""
    global _intentionanalyzer
    if _intentionanalyzer is None:
        _intentionanalyzer = IntentionAnalyzer()
    return _intentionanalyzer

# Alias para compatibilidade
def get_intention_analyzer():
    """Retorna instância de IntentionAnalyzer (alias para compatibilidade)"""
    return get_intentionanalyzer()

# Exportações
__all__ = [
    'IntentionAnalyzer',
    'get_intentionanalyzer', 
    'get_intention_analyzer'
]
