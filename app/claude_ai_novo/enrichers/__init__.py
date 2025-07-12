"""
Módulo de enriquecimento - Responsabilidade: ENRIQUECER
Contém todos os componentes para enriquecimento de dados, contexto e informações.
"""

import logging
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .semantic_enricher import SemanticEnricher
    from .enricher_manager import EnricherManager

# Configuração de logging
logger = logging.getLogger(__name__)

# Import seguro dos componentes
_components = {}

try:
    from .semantic_enricher import SemanticEnricher
    _components['SemanticEnricher'] = SemanticEnricher
except ImportError as e:
    logger.warning(f"SemanticEnricher não disponível: {e}")

try:
    from .context_enricher import ContextEnricher
    _components['ContextEnricher'] = ContextEnricher
except ImportError as e:
    logger.warning(f"ContextEnricher não disponível: {e}")

try:
    from .enricher_manager import EnricherManager
    _components['EnricherManager'] = EnricherManager
except ImportError as e:
    logger.warning(f"EnricherManager não disponível: {e}")

# Função de conveniência OBRIGATÓRIA
def get_semantic_enricher() -> Optional[Any]:
    """Retorna instância configurada do SemanticEnricher."""
    try:
        cls = _components.get('SemanticEnricher')
        if cls:
            logger.info("Criando instância SemanticEnricher")
            return cls()
        else:
            logger.warning("SemanticEnricher não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar SemanticEnricher: {e}")
        return None

def get_context_enricher() -> Optional[Any]:
    """Retorna instância configurada do ContextEnricher."""
    try:
        cls = _components.get('ContextEnricher')
        if cls:
            logger.info("Criando instância ContextEnricher")
            return cls()
        else:
            logger.warning("ContextEnricher não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ContextEnricher: {e}")
        return None

def get_enricher_manager() -> Optional[Any]:
    """Retorna instância configurada do EnricherManager."""
    try:
        cls = _components.get('EnricherManager')
        if cls:
            logger.info("Criando instância EnricherManager")
            return cls()
        else:
            logger.warning("EnricherManager não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar EnricherManager: {e}")
        return None

# Export explícito
__all__ = [
    'get_semantic_enricher',
    'get_context_enricher',
    'get_enricher_manager'
] 