"""
⚙️ PROCESSORS - Processadores de Dados
=====================================

Módulos responsáveis por processamento de dados e inteligência.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Importações com fallback robusto
try:
    from .base import BaseProcessor
    _base_processor_available = True
except ImportError as e:
    logger.warning(f"⚠️ BaseProcessor não disponível: {e}")
    _base_processor_available = False

try:
    from .context_processor import ContextProcessor, get_context_processor
    _context_processor_available = True
except ImportError as e:
    logger.warning(f"⚠️ ContextProcessor não disponível: {e}")
    _context_processor_available = False

try:
    from .query_processor import QueryProcessor, get_query_processor
    _query_processor_available = True
except ImportError as e:
    logger.warning(f"⚠️ QueryProcessor não disponível: {e}")
    _query_processor_available = False

try:
    from .data_processor import DataProcessor, get_data_processor
    _data_processor_available = True
except ImportError as e:
    logger.warning(f"⚠️ DataProcessor não disponível: {e}")
    _data_processor_available = False

try:
    from .intelligence_processor import IntelligenceProcessor, get_intelligence_processor
    _intelligence_processor_available = True
except ImportError as e:
    logger.warning(f"⚠️ IntelligenceProcessor não disponível: {e}")
    _intelligence_processor_available = False

# Instâncias globais
_context_processor_instance = None
_query_processor_instance = None
_data_processor_instance = None
_intelligence_processor_instance = None

def get_context_processor() -> Optional[object]:
    """
    Obtém instância do processador de contexto.
    
    Returns:
        Instância do ContextProcessor ou None se não disponível
    """
    global _context_processor_instance
    
    if not _context_processor_available:
        logger.warning("⚠️ ContextProcessor não está disponível")
        return None
    
    if _context_processor_instance is None:
        try:
            from .context_processor import ContextProcessor
            _context_processor_instance = ContextProcessor()
            logger.info("✅ ContextProcessor inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ContextProcessor: {e}")
            return None
    
    return _context_processor_instance

def get_query_processor() -> Optional[object]:
    """
    Obtém instância do processador de consultas.
    
    Returns:
        Instância do QueryProcessor ou None se não disponível
    """
    global _query_processor_instance
    
    if not _query_processor_available:
        logger.warning("⚠️ QueryProcessor não está disponível")
        return None
    
    if _query_processor_instance is None:
        try:
            from .query_processor import QueryProcessor
            _query_processor_instance = QueryProcessor()
            logger.info("✅ QueryProcessor inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar QueryProcessor: {e}")
            return None
    
    return _query_processor_instance

def get_data_processor() -> Optional[object]:
    """
    Obtém instância do processador de dados.
    
    Returns:
        Instância do DataProcessor ou None se não disponível
    """
    global _data_processor_instance
    
    if not _data_processor_available:
        logger.warning("⚠️ DataProcessor não está disponível")
        return None
    
    if _data_processor_instance is None:
        try:
            from .data_processor import DataProcessor
            _data_processor_instance = DataProcessor()
            logger.info("✅ DataProcessor inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar DataProcessor: {e}")
            return None
    
    return _data_processor_instance

def get_intelligence_processor() -> Optional[object]:
    """
    Obtém instância do processador de inteligência.
    
    Returns:
        Instância do IntelligenceProcessor ou None se não disponível
    """
    global _intelligence_processor_instance
    
    if not _intelligence_processor_available:
        logger.warning("⚠️ IntelligenceProcessor não está disponível")
        return None
    
    if _intelligence_processor_instance is None:
        try:
            from .intelligence_processor import IntelligenceProcessor
            _intelligence_processor_instance = IntelligenceProcessor()
            logger.info("✅ IntelligenceProcessor inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar IntelligenceProcessor: {e}")
            return None
    
    return _intelligence_processor_instance

def process_data(data: Any, processing_type: str = 'standard', **kwargs) -> Dict[str, Any]:
    """
    Processa dados usando o processador apropriado.
    
    Args:
        data: Dados para processamento
        processing_type: Tipo de processamento
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resultado do processamento
    """
    try:
        processor = get_data_processor()
        if processor and hasattr(processor, 'process_data'):
            return processor.process_data(data, processing_type, **kwargs)
        else:
            return {
                'error': 'DataProcessor não disponível',
                'fallback_data': {'type': processing_type, 'status': 'unavailable'}
            }
    except Exception as e:
        logger.error(f"❌ Erro ao processar dados: {e}")
        return {
            'error': str(e),
            'fallback_data': {'type': processing_type, 'status': 'error'}
        }

def process_query(query: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Processa consulta usando o processador de consultas.
    
    Args:
        query: Consulta a ser processada
        context: Contexto opcional
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resultado do processamento da consulta
    """
    try:
        processor = get_query_processor()
        if processor and hasattr(processor, 'process_query'):
            return processor.process_query(query, context, **kwargs)
        else:
            return {
                'error': 'QueryProcessor não disponível',
                'fallback_query': {'query': query, 'status': 'unavailable'}
            }
    except Exception as e:
        logger.error(f"❌ Erro ao processar consulta: {e}")
        return {
            'error': str(e),
            'fallback_query': {'query': query, 'status': 'error'}
        }

def process_context(context_data: Dict[str, Any], processing_type: str = 'standard', **kwargs) -> Dict[str, Any]:
    """
    Processa contexto usando o processador de contexto.
    
    Args:
        context_data: Dados de contexto
        processing_type: Tipo de processamento
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resultado do processamento de contexto
    """
    try:
        processor = get_context_processor()
        if processor and hasattr(processor, 'process_context'):
            return processor.process_context(context_data, processing_type, **kwargs)
        else:
            return {
                'error': 'ContextProcessor não disponível',
                'fallback_context': {'type': processing_type, 'status': 'unavailable'}
            }
    except Exception as e:
        logger.error(f"❌ Erro ao processar contexto: {e}")
        return {
            'error': str(e),
            'fallback_context': {'type': processing_type, 'status': 'error'}
        }

def process_intelligence(data: Any, processing_type: str = 'insights', **kwargs) -> Dict[str, Any]:
    """
    Processa dados com inteligência artificial.
    
    Args:
        data: Dados para processamento inteligente
        processing_type: Tipo de processamento ('insights', 'patterns', 'decisions', 'recommendations')
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resultado do processamento inteligente
    """
    try:
        processor = get_intelligence_processor()
        if processor and hasattr(processor, 'process_intelligence'):
            return processor.process_intelligence(data, processing_type, **kwargs)
        else:
            return {
                'error': 'IntelligenceProcessor não disponível',
                'fallback_intelligence': {'type': processing_type, 'status': 'unavailable'}
            }
    except Exception as e:
        logger.error(f"❌ Erro ao processar inteligência: {e}")
        return {
            'error': str(e),
            'fallback_intelligence': {'type': processing_type, 'status': 'error'}
        }

def synthesize_multi_source_intelligence(sources: List[Dict[str, Any]], synthesis_type: str = 'comprehensive') -> Dict[str, Any]:
    """
    Sintetiza inteligência de múltiplas fontes.
    
    Args:
        sources: Lista de fontes de dados
        synthesis_type: Tipo de síntese
        
    Returns:
        Inteligência sintetizada
    """
    try:
        processor = get_intelligence_processor()
        if processor and hasattr(processor, 'synthesize_multi_source_intelligence'):
            return processor.synthesize_multi_source_intelligence(sources, synthesis_type)
        else:
            return {
                'error': 'IntelligenceProcessor não disponível',
                'fallback_synthesis': {'type': synthesis_type, 'status': 'unavailable'}
            }
    except Exception as e:
        logger.error(f"❌ Erro na síntese multi-fonte: {e}")
        return {
            'error': str(e),
            'fallback_synthesis': {'type': synthesis_type, 'status': 'error'}
        }

def batch_process_data(data_batches: List[Any], processing_type: str = 'standard', **kwargs) -> Dict[str, Any]:
    """
    Processa dados em lotes.
    
    Args:
        data_batches: Lista de lotes de dados
        processing_type: Tipo de processamento
        **kwargs: Parâmetros adicionais
        
    Returns:
        Resultado do processamento em lote
    """
    try:
        processor = get_data_processor()
        if processor and hasattr(processor, 'batch_process'):
            return processor.batch_process(data_batches, processing_type, **kwargs)
        else:
            return {
                'error': 'DataProcessor não disponível',
                'fallback_batch': {'type': processing_type, 'status': 'unavailable'}
            }
    except Exception as e:
        logger.error(f"❌ Erro no processamento em lote: {e}")
        return {
            'error': str(e),
            'fallback_batch': {'type': processing_type, 'status': 'error'}
        }

def get_processors_status() -> Dict[str, Any]:
    """
    Obtém status dos processadores.
    
    Returns:
        Status dos processadores
    """
    return {
        'base_processor': {
            'available': _base_processor_available
        },
        'context_processor': {
            'available': _context_processor_available,
            'initialized': _context_processor_instance is not None
        },
        'query_processor': {
            'available': _query_processor_available,
            'initialized': _query_processor_instance is not None
        },
        'data_processor': {
            'available': _data_processor_available,
            'initialized': _data_processor_instance is not None
        },
        'intelligence_processor': {
            'available': _intelligence_processor_available,
            'initialized': _intelligence_processor_instance is not None
        },
        'total_processors': 5,
        'active_processors': sum([
            _base_processor_available,
            _context_processor_available,
            _query_processor_available,
            _data_processor_available,
            _intelligence_processor_available
        ])
    }

# Exportações
__all__ = [
    'get_context_processor',
    'get_query_processor',
    'get_data_processor',
    'get_intelligence_processor',
    'process_data',
    'process_query',
    'process_context',
    'process_intelligence',
    'synthesize_multi_source_intelligence',
    'batch_process_data',
    'get_processors_status'
]
