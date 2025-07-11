"""
Módulo de validação - Responsabilidade: VALIDAR
Contém todos os componentes para validação de dados, estruturas e regras.
"""

import logging
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .semantic_validator import SemanticValidator
    from .structural_validator import StructuralAI
    from .critic_validator import CriticAgent
    from ..utils.validation_utils import ValidationUtils
    from .validator_manager import ValidatorManager

# Configuração de logging
logger = logging.getLogger(__name__)

# Import seguro dos componentes
_components = {}

try:
    from .semantic_validator import SemanticValidator
    _components['SemanticValidator'] = SemanticValidator
except ImportError as e:
    logger.warning(f"SemanticValidator não disponível: {e}")

try:
    from .structural_validator import StructuralAI
    _components['StructuralAI'] = StructuralAI
except ImportError as e:
    logger.warning(f"StructuralValidator não disponível: {e}")

try:
    from .critic_validator import CriticAgent
    _components['CriticAgent'] = CriticAgent
except ImportError as e:
    logger.warning(f"CriticValidator não disponível: {e}")

try:
    from ..utils.validation_utils import ValidationUtils
    _components['ValidationUtils'] = ValidationUtils
except ImportError as e:
    logger.warning(f"DataValidator não disponível: {e}")

try:
    from .validator_manager import ValidatorManager
    _components['ValidatorManager'] = ValidatorManager
except ImportError as e:
    logger.warning(f"ValidatorManager não disponível: {e}")

# Funções de conveniência OBRIGATÓRIAS
def get_semantic_validator(orchestrator=None) -> Optional[Any]:
    """Retorna instância configurada do SemanticValidator."""
    try:
        cls = _components.get('SemanticValidator')
        if cls and orchestrator:
            logger.info("Criando instância SemanticValidator")
            return cls(orchestrator)
        else:
            logger.warning("SemanticValidator não disponível ou orchestrator não fornecido")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar SemanticValidator: {e}")
        return None

def get_structural_validator() -> Optional[Any]:
    """Retorna instância configurada do StructuralValidator."""
    try:
        cls = _components.get('StructuralAI')
        if cls:
            logger.info("Criando instância StructuralValidator")
            return cls()
        else:
            logger.warning("StructuralValidator não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar StructuralValidator: {e}")
        return None

def get_data_validator() -> Optional[Any]:
    """Retorna instância configurada do DataValidator."""
    try:
        cls = _components.get('ValidationUtils')
        if cls:
            logger.info("Criando instância DataValidator")
            return cls()
        else:
            logger.warning("DataValidator não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar DataValidator: {e}")
        return None

def get_critic_validator(orchestrator=None) -> Optional[Any]:
    """Retorna instância configurada do CriticValidator."""
    try:
        cls = _components.get('CriticAgent')
        if cls and orchestrator:
            logger.info("Criando instância CriticValidator")
            return cls(orchestrator)
        else:
            logger.warning("CriticValidator não disponível ou orchestrator não fornecido")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar CriticValidator: {e}")
        return None

def get_validator_manager(orchestrator=None) -> Optional[Any]:
    """Retorna instância configurada do ValidatorManager."""
    try:
        cls = _components.get('ValidatorManager')
        if cls:
            logger.info("Criando instância ValidatorManager")
            return cls(orchestrator)
        else:
            logger.warning("ValidatorManager não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ValidatorManager: {e}")
        return None

# Flask fallback para execução standalone
def validate_context(field: str, model: str, value: Optional[str] = None) -> dict:
    """Função de conveniência para validação de contexto."""
    try:
        manager = get_validator_manager()
        if manager:
            return manager.validate_context(field, model, value)
        return {'error': 'ValidatorManager não disponível', 'valid': False}
    except Exception as e:
        logger.error(f"Erro ao validar contexto: {e}")
        return {'error': str(e), 'valid': False}

def validate_data_structure(data: dict) -> dict:
    """Função de conveniência para validação de estrutura de dados."""
    try:
        manager = get_validator_manager()
        if manager:
            return manager.validate_data_structure(data)
        return {'error': 'ValidatorManager não disponível', 'valid': False}
    except Exception as e:
        logger.error(f"Erro ao validar estrutura: {e}")
        return {'error': str(e), 'valid': False}

def get_validation_status() -> dict:
    """Função de conveniência para status das validações."""
    try:
        manager = get_validator_manager()
        if manager:
            return manager.get_validation_status()
        return {'error': 'ValidatorManager não disponível'}
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return {'error': str(e)}

# Export explícito
__all__ = [
    'get_semantic_validator',
    'get_structural_validator',
    'get_critic_validator',
    'get_data_validator',
    'get_validator_manager',
    'validate_context',
    'validate_data_structure',
    'get_validation_status'
]

# Execução standalone
if __name__ == "__main__":
    print("✅ VALIDATORS - Testando componentes")
    
    # Teste do ValidatorManager
    manager = get_validator_manager()
    if manager:
        print("✅ ValidatorManager OK")
        status = manager.get_validation_status()
        print(f"📊 Validadores disponíveis: {len(status.get('validators', {}))}")
    else:
        print("❌ ValidatorManager não disponível")
    
    # Teste dos componentes individuais
    components = ['SemanticValidator', 'StructuralAI', 'CriticAgent', 'ValidationUtils']
    for component in components:
        if component in _components:
            print(f"✅ {component} OK")
        else:
            print(f"❌ {component} não disponível")
    
    print("✅ Teste concluído") 