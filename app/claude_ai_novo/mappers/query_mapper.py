"""
🗺️ QUERY MAPPER - Mapeador de Consultas
=======================================

Responsabilidade: MAPEAR consultas entre diferentes formatos
(natural language, SQL, API, etc.)

Autor: Claude AI Novo
Data: 2025-01-07
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Tipos de consulta suportados"""
    NATURAL_LANGUAGE = "natural_language"
    SQL = "sql"
    API = "api"
    FILTER = "filter"
    SEARCH = "search"

@dataclass
class QueryMapping:
    """Definição de mapeamento de consulta"""
    source_type: QueryType
    target_type: QueryType
    pattern: str
    template: str
    parameters: Dict[str, Any] = None

class QueryMapper:
    """
    Mapeador de consultas entre diferentes formatos.
    
    Converte consultas de linguagem natural para SQL, API calls, etc.
    """
    
    def __init__(self):
        self.mappings: Dict[str, List[QueryMapping]] = {}
        self.query_cache: Dict[str, Any] = {}
        self._setup_default_mappings()
    
    def _setup_default_mappings(self):
        """Configura mapeamentos padrão"""
        # Mapeamentos de linguagem natural para SQL
        self.add_mapping("pedidos_sql", QueryMapping(
            source_type=QueryType.NATURAL_LANGUAGE,
            target_type=QueryType.SQL,
            pattern="pedidos do cliente {cliente}",
            template="SELECT * FROM pedidos WHERE cliente ILIKE '%{cliente}%'"
        ))
        
        self.add_mapping("entregas_sql", QueryMapping(
            source_type=QueryType.NATURAL_LANGUAGE,
            target_type=QueryType.SQL,
            pattern="entregas atrasadas",
            template="SELECT * FROM entregas_monitoradas WHERE entregue = false AND data_prevista_entrega < NOW()"
        ))
    
    def add_mapping(self, mapping_name: str, query_mapping: QueryMapping):
        """
        Adiciona um mapeamento de consulta.
        
        Args:
            mapping_name: Nome do mapeamento
            query_mapping: Definição do mapeamento
        """
        if mapping_name not in self.mappings:
            self.mappings[mapping_name] = []
        
        self.mappings[mapping_name].append(query_mapping)
        logger.debug(f"Mapeamento de consulta adicionado: {mapping_name}")
    
    def map_query(self, query: str, target_type: QueryType = QueryType.SQL) -> Optional[str]:
        """
        Mapeia uma consulta para o tipo de destino especificado.
        
        Args:
            query: Consulta de origem
            target_type: Tipo de consulta de destino
            
        Returns:
            Consulta mapeada ou None se não encontrado
        """
        # Normalizar consulta
        normalized_query = query.lower().strip()
        
        # Buscar por mapeamentos
        for mapping_group in self.mappings.values():
            for mapping in mapping_group:
                if mapping.target_type == target_type:
                    # Verificar se o padrão corresponde
                    if self._pattern_matches(normalized_query, mapping.pattern):
                        # Extrair parâmetros
                        params = self._extract_parameters(normalized_query, mapping.pattern)
                        
                        # Aplicar template
                        mapped_query = self._apply_template(mapping.template, params)
                        
                        logger.info(f"Consulta mapeada: {query} -> {mapped_query}")
                        return mapped_query
        
        logger.warning(f"Nenhum mapeamento encontrado para: {query}")
        return None
    
    def _pattern_matches(self, query: str, pattern: str) -> bool:
        """
        Verifica se a consulta corresponde ao padrão.
        
        Args:
            query: Consulta a verificar
            pattern: Padrão a comparar
            
        Returns:
            True se corresponde
        """
        # Implementação simples - pode ser melhorada com regex
        pattern_words = pattern.lower().replace("{", "").replace("}", "").split()
        return all(word in query for word in pattern_words if word not in ["{", "}"])
    
    def _extract_parameters(self, query: str, pattern: str) -> Dict[str, str]:
        """
        Extrai parâmetros da consulta baseado no padrão.
        
        Args:
            query: Consulta de origem
            pattern: Padrão com placeholders
            
        Returns:
            Dicionário com parâmetros extraídos
        """
        params = {}
        
        # Implementação simples - pode ser melhorada
        if "{cliente}" in pattern:
            # Tentar extrair nome do cliente
            words = query.split()
            for i, word in enumerate(words):
                if word in ["cliente", "do", "da"]:
                    if i + 1 < len(words):
                        params["cliente"] = words[i + 1]
                        break
        
        return params
    
    def _apply_template(self, template: str, params: Dict[str, str]) -> str:
        """
        Aplica parâmetros ao template.
        
        Args:
            template: Template da consulta
            params: Parâmetros a aplicar
            
        Returns:
            Template com parâmetros aplicados
        """
        result = template
        for key, value in params.items():
            result = result.replace(f"{{{key}}}", value)
        
        return result

# Instância global
_query_mapper = None

def get_query_mapper() -> QueryMapper:
    """
    Retorna instância global do QueryMapper.
    
    Returns:
        QueryMapper: Instância do mapeador
    """
    global _query_mapper
    if _query_mapper is None:
        _query_mapper = QueryMapper()
        logger.info("✅ QueryMapper inicializado")
    return _query_mapper

# Exports
__all__ = [
    'QueryMapper',
    'QueryMapping',
    'QueryType',
    'get_query_mapper'
] 