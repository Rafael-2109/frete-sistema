"""
⚙️ CONFIGURAÇÕES CLAUDE AI
Configurações centralizadas do módulo
"""

import os
from typing import Dict, Any

class ClaudeAIConfig:
    """Configurações do Claude AI"""
    
    # Claude API
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 8192
    TEMPERATURE = 0.7
    
    # Contexto conversacional
    CONTEXT_MAX_MESSAGES = 20
    CONTEXT_TTL_HOURS = 1
    
    # Cache Redis
    REDIS_PREFIX = "claude_ai:"
    CACHE_TTL_SECONDS = 300
    
    # Aprendizado
    LEARNING_MIN_CONFIDENCE = 0.4
    LEARNING_MAX_PATTERNS = 1000
    
    # Performance
    MAX_CONCURRENT_REQUESTS = 10
    REQUEST_TIMEOUT_SECONDS = 120
    
    # Logs
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/claude_ai.log"
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Converte configurações para dicionário"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and not callable(getattr(cls, key))
        }
    
    @classmethod
    def validate(cls) -> bool:
        """Valida configurações obrigatórias"""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY não configurada")
        return True
