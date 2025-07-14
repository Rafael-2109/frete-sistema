"""
🗺️ FIELD MAPPER - Mapeador de Campos
===================================

Responsabilidade: MAPEAR campos entre diferentes representações
(banco de dados, API, interface, etc.)

Autor: Claude AI Novo
Data: 2025-01-07
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FieldType(Enum):
    """Tipos de campos suportados"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"

@dataclass
class FieldMapping:
    """Definição de mapeamento de campo"""
    source_field: str
    target_field: str
    field_type: FieldType
    required: bool = False
    default_value: Any = None
    transform_function: Optional[Callable] = None
    validation_function: Optional[Callable] = None

class FieldMapper:
    """
    Mapeador de campos entre diferentes representações.
    
    Permite mapear campos de uma estrutura para outra, aplicando
    transformações e validações conforme necessário.
    """
    
    def __init__(self):
        self.mappings: Dict[str, List[FieldMapping]] = {}
        self.transformers: Dict[str, Callable] = {}
        self.validators: Dict[str, Callable] = {}
        self._setup_default_transformers()
        self._setup_default_validators()
    
    def _setup_default_transformers(self):
        """Configura transformadores padrão"""
        self.transformers.update({
            'to_string': lambda x: str(x) if x is not None else '',
            'to_int': lambda x: int(x) if x is not None else 0,
            'to_float': lambda x: float(x) if x is not None else 0.0,
            'to_bool': lambda x: bool(x) if x is not None else False,
            'to_upper': lambda x: str(x).upper() if x is not None else '',
            'to_lower': lambda x: str(x).lower() if x is not None else '',
            'strip_spaces': lambda x: str(x).strip() if x is not None else '',
            'format_currency': lambda x: f"R$ {float(x):,.2f}" if x is not None else "R$ 0,00"
        })
    
    def _setup_default_validators(self):
        """Configura validadores padrão"""
        self.validators.update({
            'not_empty': lambda x: x is not None and str(x).strip() != '',
            'is_numeric': lambda x: str(x).replace('.', '').replace(',', '').isdigit() if x else False,
            'is_email': lambda x: '@' in str(x) if x else False,
            'min_length': lambda x, min_len=1: len(str(x)) >= min_len if x else False,
            'max_length': lambda x, max_len=255: len(str(x)) <= max_len if x else True
        })
    
    def add_mapping(self, mapping_name: str, field_mapping: FieldMapping):
        """
        Adiciona um mapeamento de campo.
        
        Args:
            mapping_name: Nome do conjunto de mapeamentos
            field_mapping: Definição do mapeamento
        """
        if mapping_name not in self.mappings:
            self.mappings[mapping_name] = []
        
        self.mappings[mapping_name].append(field_mapping)
        logger.debug(f"Mapeamento adicionado: {mapping_name} -> {field_mapping.source_field} : {field_mapping.target_field}")
    
    def map_fields(self, mapping_name: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapeia campos de acordo com o mapeamento especificado.
        
        Args:
            mapping_name: Nome do conjunto de mapeamentos
            source_data: Dados de origem
            
        Returns:
            Dados mapeados
        """
        if mapping_name not in self.mappings:
            logger.error(f"Mapeamento não encontrado: {mapping_name}")
            return {}
        
        mapped_data = {}
        mappings = self.mappings[mapping_name]
        
        for mapping in mappings:
            try:
                # Obter valor do campo de origem
                source_value = source_data.get(mapping.source_field)
                
                # Aplicar valor padrão se necessário
                if source_value is None and mapping.default_value is not None:
                    source_value = mapping.default_value
                
                # Verificar campo obrigatório
                if mapping.required and source_value is None:
                    logger.warning(f"Campo obrigatório ausente: {mapping.source_field}")
                    continue
                
                # Aplicar transformação se especificada
                if mapping.transform_function:
                    source_value = mapping.transform_function(source_value)
                
                # Aplicar validação se especificada
                if mapping.validation_function and not mapping.validation_function(source_value):
                    logger.warning(f"Validação falhou para campo: {mapping.source_field}")
                    continue
                
                # Mapear para campo de destino
                mapped_data[mapping.target_field] = source_value
                
            except Exception as e:
                logger.error(f"Erro ao mapear campo {mapping.source_field}: {e}")
                continue
        
        logger.info(f"Mapeamento '{mapping_name}' concluído: {len(mapped_data)} campos mapeados")
        return mapped_data
    
    def create_pedidos_mapping(self):
        """Cria mapeamento padrão para pedidos"""
        mappings = [
            FieldMapping("num_pedido", "numero_pedido", FieldType.STRING, required=True),
            FieldMapping("cliente", "nome_cliente", FieldType.STRING, required=True),
            FieldMapping("valor", "valor_total", FieldType.FLOAT, transform_function=self.transformers['to_float']),
            FieldMapping("data_pedido", "data_criacao", FieldType.DATE),
            FieldMapping("status", "status_pedido", FieldType.STRING, transform_function=self.transformers['to_upper'])
        ]
        
        for mapping in mappings:
            self.add_mapping("pedidos", mapping)

# Instância global
_field_mapper = None

def get_field_mapper() -> FieldMapper:
    """
    Retorna instância global do FieldMapper.
    
    Returns:
        FieldMapper: Instância do mapeador
    """
    global _field_mapper
    if _field_mapper is None:
        _field_mapper = FieldMapper()
        _field_mapper.create_pedidos_mapping()
        logger.info("✅ FieldMapper inicializado")
    return _field_mapper

# Exports
__all__ = [
    'FieldMapper',
    'FieldMapping',
    'FieldType',
    'get_field_mapper'
] 