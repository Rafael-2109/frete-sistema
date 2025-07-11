"""
📋 MAPPERS - Mapeamentos Semânticos por Modelo
==============================================

Módulo contendo mapeadores específicos para cada modelo de dados.
Organizados com MapperManager coordenando mappers especializados.
"""

import logging

logger = logging.getLogger(__name__)

# Flask fallback para execução standalone
try:
    from app.claude_ai_novo.utils.flask_fallback import is_flask_available
    flask_available = is_flask_available()
except ImportError:
    flask_available = False
    logger.warning("Flask fallback não disponível")

# Imports principais
try:
    # Manager principal
    from .mapper_manager import MapperManager, get_mapper_manager
    
    # Mappers específicos
    from .context_mapper import ContextMapper, get_context_mapper
    from .field_mapper import FieldMapper, get_field_mapper
    from .query_mapper import QueryMapper, get_query_mapper
    
    # Mappers de domínio
    from .domain.base_mapper import BaseMapper
    from .domain.pedidos_mapper import PedidosMapper
    from .domain.embarques_mapper import EmbarquesMapper
    from .domain.monitoramento_mapper import MonitoramentoMapper
    from .domain.faturamento_mapper import FaturamentoMapper
    from .domain.transportadoras_mapper import TransportadorasMapper
    
    # Aliases para compatibilidade
    from .mapper_manager import SemanticMapper, get_semantic_mapper
    
    logger.info("✅ Mappers carregados com sucesso")
    
except ImportError as e:
    logger.warning(f"⚠️ Erro ao carregar mappers: {e}")
    
    # Fallback básico
    class FallbackMapper:
        def __init__(self, nome="fallback"): 
            self.nome = nome
        def buscar_mapeamento(self, termo): 
            return []
        def analisar_consulta_semantica(self, query): 
            return {"campos_detectados": [], "confianca": 0.0}
        def map_fields(self, mapping_name, source_data):
            return {}
        def get_best_mapper_for_query(self, query):
            return self
    
    # Atribuir classes fallback
    MapperManager = FallbackMapper
    ContextMapper = FallbackMapper
    FieldMapper = FallbackMapper
    QueryMapper = FallbackMapper
    BaseMapper = FallbackMapper
    PedidosMapper = FallbackMapper
    EmbarquesMapper = FallbackMapper
    MonitoramentoMapper = FallbackMapper
    FaturamentoMapper = FallbackMapper
    TransportadorasMapper = FallbackMapper
    SemanticMapper = FallbackMapper
    
    # Funções fallback
    def get_mapper_manager(): return MapperManager()
    def get_context_mapper(): return ContextMapper()
    def get_field_mapper(): return FieldMapper()
    def get_query_mapper(): return QueryMapper()
    def get_semantic_mapper(): return SemanticMapper()

# Funções de conveniência para mapeamento rápido
def map_query_fields(query: str, mapping_name: str = "default"):
    """Mapeamento rápido de campos de consulta"""
    field_mapper = get_field_mapper()
    return field_mapper.map_fields(mapping_name, {"query": query})

def analyze_query_mapping(query: str):
    """Análise rápida de mapeamento de consulta"""
    query_mapper = get_query_mapper()
    return query_mapper.analisar_consulta_semantica(query)

def get_best_mapper_for_domain(domain: str):
    """Retorna o melhor mapper para um domínio específico"""
    domain_mappers = {
        'pedidos': get_field_mapper,
        'embarques': get_field_mapper,
        'monitoramento': get_field_mapper,
        'faturamento': get_field_mapper,
        'transportadoras': get_field_mapper
    }
    
    mapper_func = domain_mappers.get(domain.lower(), get_field_mapper)
    return mapper_func()

__all__ = [
    # Manager principal
    'MapperManager',
    'get_mapper_manager',
    
    # Mappers específicos
    'ContextMapper',
    'FieldMapper', 
    'QueryMapper',
    'get_context_mapper',
    'get_field_mapper',
    'get_query_mapper',
    
    # Mappers de domínio
    'BaseMapper',
    'PedidosMapper',
    'EmbarquesMapper', 
    'MonitoramentoMapper',
    'FaturamentoMapper',
    'TransportadorasMapper',
    
    # Compatibilidade
    'SemanticMapper',
    'get_semantic_mapper',
    
    # Funções de conveniência
    'map_query_fields',
    'analyze_query_mapping',
    'get_best_mapper_for_domain'
]