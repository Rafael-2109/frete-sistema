"""
🗺️ CONTEXT MAPPER - Mapeador de Contexto
========================================

Responsabilidade: MAPEAR contextos entre diferentes representações
(usuário, sessão, ambiente, etc.)

Autor: Claude AI Novo
Data: 2025-01-07
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ContextMapping:
    """Definição de mapeamento de contexto"""
    context_type: str
    source_keys: List[str]
    target_key: str
    transform_function: Optional[callable] = None
    priority: int = 0

class ContextMapper:
    """
    Mapeador de contextos entre diferentes representações.
    
    Permite mapear contextos de uma estrutura para outra,
    consolidando informações de múltiplas fontes.
    """
    
    def __init__(self):
        self.mappings: Dict[str, List[ContextMapping]] = {}
        self.context_cache: Dict[str, Any] = {}
        self._setup_default_mappings()
    
    def _setup_default_mappings(self):
        """Configura mapeamentos padrão"""
        self.add_mapping("user_context", ContextMapping(
            context_type="user",
            source_keys=["user_id", "nome", "perfil"],
            target_key="user_info"
        ))
        
        self.add_mapping("session_context", ContextMapping(
            context_type="session",
            source_keys=["session_id", "timestamp", "ip_address"],
            target_key="session_info"
        ))
    
    def add_mapping(self, mapping_name: str, context_mapping: ContextMapping):
        """
        Adiciona um mapeamento de contexto.
        
        Args:
            mapping_name: Nome do mapeamento
            context_mapping: Definição do mapeamento
        """
        if mapping_name not in self.mappings:
            self.mappings[mapping_name] = []
        
        self.mappings[mapping_name].append(context_mapping)
        logger.debug(f"Mapeamento de contexto adicionado: {mapping_name}")
    
    def map_context(self, mapping_name: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapeia contexto de acordo com o mapeamento especificado.
        
        Args:
            mapping_name: Nome do mapeamento
            source_data: Dados de origem
            
        Returns:
            Contexto mapeado
        """
        if mapping_name not in self.mappings:
            logger.error(f"Mapeamento de contexto não encontrado: {mapping_name}")
            return {}
        
        mapped_context = {}
        mappings = self.mappings[mapping_name]
        
        for mapping in sorted(mappings, key=lambda x: x.priority, reverse=True):
            try:
                # Coletar valores das chaves de origem
                context_values = {}
                for key in mapping.source_keys:
                    if key in source_data:
                        context_values[key] = source_data[key]
                
                # Aplicar transformação se especificada
                if mapping.transform_function:
                    context_values = mapping.transform_function(context_values)
                
                # Mapear para chave de destino
                mapped_context[mapping.target_key] = context_values
                
            except Exception as e:
                logger.error(f"Erro ao mapear contexto {mapping.target_key}: {e}")
                continue
        
        logger.info(f"Contexto '{mapping_name}' mapeado com sucesso")
        return mapped_context

# Instância global
_context_mapper = None

def get_context_mapper() -> ContextMapper:
    """
    Retorna instância global do ContextMapper.
    
    Returns:
        ContextMapper: Instância do mapeador
    """
    global _context_mapper
    if _context_mapper is None:
        _context_mapper = ContextMapper()
        logger.info("✅ ContextMapper inicializado")
    return _context_mapper

# Exports
__all__ = [
    'ContextMapper',
    'ContextMapping',
    'get_context_mapper'
] 