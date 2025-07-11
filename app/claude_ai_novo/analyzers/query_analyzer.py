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
from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
from app.utils.api_helper import get_system_alerts
from app.utils.ai_logging import ai_logger, AILogger
from app.utils.redis_cache import intelligent_cache
import time
import asyncio
from app.utils.grupo_empresarial import GrupoEmpresarialDetector
from app.fretes.models import Frete
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from app.pedidos.models import Pedido
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.fretes.models import Frete, DespesaExtra
from app.monitoramento.models import AgendamentoEntrega
from app.utils.grupo_empresarial import detectar_grupo_empresarial
from app.embarques.models import Embarque, EmbarqueItem
from datetime import date
from app.faturamento.models import RelatorioFaturamentoImportado as RelatorioImportado
from app.fretes.models import DespesaExtra
from app.financeiro.models import PendenciaFinanceiraNF

# Configurar logger
logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """Analisador de consultas avançado"""
    
    def __init__(self):
        pass
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analisa estrutura e características da consulta"""
        query_lower = query.lower()
        words = query.split()
        
        # Detectar tipo de consulta
        query_type = self._detect_query_type(query_lower)
        
        # Calcular complexidade
        complexity = self._calculate_complexity(query, words)
        
        # Detectar domínios
        domains = self._detect_domains(query_lower)
        
        # Detectar entidades
        entities = self._extract_entities(query_lower)
        
        # Detectar padrões temporais
        temporal_patterns = self._detect_temporal_patterns(query_lower)
        
        return {
            'query_type': query_type,
            'complexity': complexity,
            'domains': domains,
            'entities': entities,
            'temporal_patterns': temporal_patterns,
            'word_count': len(words),
            'character_count': len(query),
            'has_question_words': self._has_question_words(query_lower),
            'urgency_level': self._detect_urgency(query_lower)
        }
    
    def _detect_query_type(self, query: str) -> str:
        """Detecta o tipo da consulta"""
        if any(word in query for word in ['?', 'qual', 'quanto', 'quantos', 'como', 'onde', 'quando']):
            return 'question'
        elif any(word in query for word in ['gerar', 'criar', 'exportar', 'fazer']):
            return 'command'
        elif any(word in query for word in ['listar', 'mostrar', 'ver', 'status']):
            return 'request'
        else:
            return 'statement'
    
    def _calculate_complexity(self, query: str, words: list) -> float:
        """Calcula complexidade da consulta (0-1)"""
        complexity = 0.0
        
        # Baseado no tamanho
        complexity += min(len(words) / 20, 0.3)
        
        # Baseado em conjunções
        conjunctions = ['e', 'ou', 'mas', 'porém', 'entretanto']
        complexity += sum(0.1 for conj in conjunctions if conj in query.lower())
        
        # Baseado em filtros
        filters = ['hoje', 'ontem', 'semana', 'mês', 'ano', 'status', 'tipo']
        complexity += sum(0.05 for filt in filters if filt in query.lower())
        
        return min(complexity, 1.0)
    
    def _detect_domains(self, query: str) -> List[str]:
        """Detecta domínios relacionados à consulta"""
        domains = []
        
        domain_keywords = {
            'entregas': ['entrega', 'transportadora', 'agendamento', 'atraso'],
            'fretes': ['frete', 'custo', 'valor', 'cotação'],
            'pedidos': ['pedido', 'cliente', 'produto'],
            'financeiro': ['faturamento', 'pagamento', 'pendência'],
            'embarques': ['embarque', 'separação', 'estoque']
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in query for keyword in keywords):
                domains.append(domain)
        
        return domains if domains else ['general']
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extrai entidades nomeadas básicas com inteligência empresarial e geográfica"""
        entities = []
        
        # 1. DETECÇÃO INTELIGENTE DE GRUPOS EMPRESARIAIS
        try:
            detector_grupos = GrupoEmpresarialDetector()
            grupo_detectado = detector_grupos.detectar_grupo_na_consulta(query)
            
            if grupo_detectado:
                entities.append(f"grupo_empresarial:{grupo_detectado['grupo_detectado']}")
                
                # Adicionar empresas específicas do grupo se detectadas
                empresas_grupo = grupo_detectado.get('empresas_relacionadas', [])
                for empresa in empresas_grupo[:3]:  # Limitar a 3 para não poluir
                    entities.append(f"empresa:{empresa}")
        except Exception as e:
            logger.debug(f"Erro na detecção de grupos empresariais: {e}")
        
        # 2. EMPRESAS INDIVIDUAIS (fallback se grupo não detectado)
        if not any('grupo_empresarial:' in entity for entity in entities):
            empresas_conhecidas = ['assai', 'atacadao', 'carrefour', 'tenda', 'mateus', 'coco bambu', 'fort']
            for empresa in empresas_conhecidas:
                if empresa in query.lower():
                    entities.append(f"empresa:{empresa}")
        
        # 3. DETECÇÃO GEOGRÁFICA COMPLETA (usar utils/ufs.py)
        try:
            from app.utils.ufs import UF_LIST
            
            # Extrair apenas as siglas dos estados
            estados_disponiveis = [uf[0].lower() for uf in UF_LIST]
            
            # Detectar estados na consulta
            query_words = query.lower().split()
            for word in query_words:
                if word in estados_disponiveis:
                    entities.append(f"estado:{word.upper()}")
                    
                # Detectar padrões como "SP", "em SP", "de SP", etc.
                for uf_code, uf_name in UF_LIST:
                    if f" {uf_code.lower()} " in f" {query.lower()} ":
                        entities.append(f"estado:{uf_code}")
                        break
                        
        except Exception as e:
            logger.debug(f"Erro na detecção geográfica: {e}")
            # Fallback para lista reduzida
            estados_basicos = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
            for estado in estados_basicos:
                if f" {estado} " in f" {query.lower()} ":
                    entities.append(f"estado:{estado.upper()}")
      
        return entities
    
    def _detect_temporal_patterns(self, query: str) -> List[str]:
        """Detecta padrões temporais na consulta"""
        patterns = []
        
        temporal_words = {
            'today': ['hoje', 'hj'],
            'yesterday': ['ontem'],
            'week': ['semana', 'semanal'],
            'month': ['mês', 'mensal'],
            'year': ['ano', 'anual'],
            'urgent': ['urgente', 'emergência', 'imediato']
        }
        
        for pattern, words in temporal_words.items():
            if any(word in query for word in words):
                patterns.append(pattern)
        
        return patterns
    
    def _has_question_words(self, query: str) -> bool:
        """Verifica se tem palavras interrogativas"""
        question_words = ['qual', 'quanto', 'quantos', 'como', 'onde', 'quando', 'por que', 'o que']
        return any(word in query for word in question_words)
    
    def _detect_urgency(self, query: str) -> str:
        """Detecta nível de urgência"""
        if any(word in query for word in ['urgente', 'emergência', 'imediato', 'agora']):
            return 'high'
        elif any(word in query for word in ['hoje', 'rápido', 'preciso']):
            return 'medium'
        else:
            return 'low'

# Instância global
_query_analyzer = None

def get_query_analyzer():
    """Retorna instância de QueryAnalyzer"""
    global _query_analyzer
    if _query_analyzer is None:
        _query_analyzer = QueryAnalyzer()
    return _query_analyzer

# Exportações
__all__ = [
    'QueryAnalyzer',
    'get_query_analyzer'
]