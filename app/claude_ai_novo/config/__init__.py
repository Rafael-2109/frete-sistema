"""
📦 CONFIG - Configurações Centralizadas
Módulo de configurações do Claude AI
"""

# Importações principais
try:
    from .advanced_config import get_advanced_config, is_unlimited_mode
    __all__ = ['get_advanced_config', 'is_unlimited_mode']
except ImportError:
    __all__ = []

# Versão do módulo
__version__ = "1.0.0"

# Configurações padrão
DEFAULT_CONFIG = {
    'max_tokens': 8192,
    'temperature': 0.1,
    'timeout': 90
} 