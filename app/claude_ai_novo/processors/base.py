#!/usr/bin/env python3
"""
Processors Base - Framework base para todos os processors
Versão focada em processamento de dados e análise
Herda infraestrutura base de utils/base_classes.py
"""

import re
import time
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union

# Import da classe base de infraestrutura
from app.claude_ai_novo.utils.base_classes import BaseProcessor as BaseInfrastructure

logger = logging.getLogger(__name__)

class ProcessorBase(BaseInfrastructure):
    """
    Classe base específica para processamento de dados
    Herda infraestrutura de utils/base_classes.py
    Adiciona funcionalidades específicas de processamento
    
    Uso: Para todos os processors que precisam de funcionalidades de processamento
    """
    
    def __init__(self):
        # Inicializar infraestrutura base
        super().__init__()
        
        # Adicionar tracking específico de processamento
        self._cache_hits = 0
        self._cache_misses = 0
        
    # ==============================
    # FUNCIONALIDADES ESPECÍFICAS DE PROCESSAMENTO
    # ==============================
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extrai filtros específicos da consulta de processamento"""
        filtros = {}
        query_lower = query.lower()
        
        # Cliente - específico para sistema de fretes
        clientes_comuns = [
            'assai', 'atacadão', 'carrefour', 'tenda', 'mateus', 'coco bambu',
            'fort', 'renner', 'americanas', 'b2w'
        ]
        
        for cliente in clientes_comuns:
            if cliente in query_lower:
                filtros['cliente'] = cliente.title()
                break
        
        # Período temporal - específico para análise de dados
        if 'hoje' in query_lower:
            filtros['periodo'] = 'hoje'
            filtros['data_inicio'] = datetime.now().date()
            filtros['data_fim'] = datetime.now().date()
        elif 'semana' in query_lower or 'últimos 7 dias' in query_lower:
            filtros['periodo'] = 'semana'
            filtros['data_inicio'] = datetime.now().date() - timedelta(days=7)
            filtros['data_fim'] = datetime.now().date()
        elif 'mês' in query_lower or 'mes' in query_lower:
            filtros['periodo'] = 'mes'
            filtros['data_inicio'] = datetime.now().date() - timedelta(days=30)
            filtros['data_fim'] = datetime.now().date()
        
        # Status - específico para sistema de fretes
        if 'pendente' in query_lower:
            filtros['status'] = 'pendente'
        elif 'aprovado' in query_lower:
            filtros['status'] = 'aprovado'
        elif 'entregue' in query_lower:
            filtros['status'] = 'entregue'
        
        return filtros
    
    # ==============================
    # CACHE COM TRACKING DE PERFORMANCE
    # ==============================
    
    def _get_cached_result(self, cache_key: str, ttl: int = 300) -> Optional[Any]:
        """
        Busca resultado em cache com tracking de performance
        Sobrescreve método base para adicionar estatísticas
        """
        result = super()._get_cached_result(cache_key, ttl)
        
        if result is not None:
            self._cache_hits += 1
        else:
            self._cache_misses += 1
            
        return result
    
    def get_cache_stats(self) -> Dict[str, Union[int, float]]:
        """Retorna estatísticas específicas de cache do processamento"""
        total_requests = self._cache_hits + self._cache_misses
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': (self._cache_hits / total_requests) * 100 if total_requests > 0 else 0,
            'total_requests': total_requests
        }
    
    # ==============================
    # FORMATAÇÃO ESPECÍFICA DE PROCESSAMENTO
    # ==============================
    
    def _format_weight(self, peso: Union[int, float]) -> str:
        """Formata peso com lógica específica para sistema de fretes"""
        try:
            peso_float = float(peso)
            if peso_float >= 1000:
                return f"{peso_float/1000:.1f}t"
            return f"{peso_float:.1f}kg"
        except (ValueError, TypeError):
            return "0kg"
    
    def _format_percentage(self, valor: Union[int, float], decimais: int = 1) -> str:
        """Formata porcentagem com decimais configuráveis"""
        try:
            return f"{float(valor):.{decimais}f}%"
        except (ValueError, TypeError):
            return "0%"
    
    # ==============================
    # ESTATÍSTICAS DE PROCESSAMENTO
    # ==============================
    
    def _create_summary_stats(self, dados: List[Any], tipo: str) -> Dict[str, Any]:
        """Cria estatísticas resumidas específicas para processamento"""
        if not dados:
            return {'total': 0, 'tipo': tipo}
        
        stats = {
            'total': len(dados),
            'tipo': tipo,
            'data_analise': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'cache_stats': self.get_cache_stats()
        }
        
        return stats
    
    # ==============================
    # OVERRIDE DE LOGGING PARA PROCESSAMENTO
    # ==============================
    
    def _handle_error(self, error: Exception, operation: str, context: Optional[str] = None) -> str:
        """
        Tratamento de erros específico para processamento
        Mantém padrão mais simples que a infraestrutura base
        """
        error_id = f"{operation}_{int(time.time())}"
        
        self.logger.error(
            f"❌ [{error_id}] {operation} | Erro: {error} | Contexto: {context or 'N/A'}"
        )
        
        return f"Erro {error_id}: {error}"

# ==============================
# FUNÇÕES DE CONVENIÊNCIA ESPECÍFICAS
# ==============================

def get_base_processor() -> ProcessorBase:
    """Retorna instância do ProcessorBase de processamento"""
    return ProcessorBase()

# Alias para compatibilidade
BaseProcessor = ProcessorBase

def format_response(content: str, processor_type: str = "processor") -> str:
    """Formata resposta específica para processamento"""
    footer = f"""
---
🔄 **{processor_type} - Processado com sucesso**
🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
    
    return content + footer

# ==============================
# EXPORTS ESPECÍFICOS DE PROCESSAMENTO
# ==============================

__all__ = [
    # Classe principal
    'ProcessorBase',
    'BaseProcessor',  # Alias para compatibilidade
    
    # Functions específicas
    'get_base_processor',
    'format_response',
    
    # Re-export da infraestrutura base (para compatibilidade)
    'logging',
    'datetime',
] 