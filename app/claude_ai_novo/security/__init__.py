#!/usr/bin/env python3
"""
🔐 SECURITY - Módulo de Segurança
=================================

Módulo responsável pela segurança do sistema Claude AI Novo.
SecurityGuard atua como manager único - não necessita de manager adicional.
"""

import logging
from typing import Optional

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
    from .security_guard import (
        SecurityGuard,
        get_security_guard,
        validate_user_access,
        validate_input,
        sanitize_input
    )
    
    logger.info("✅ Security carregado com sucesso")
    
except ImportError as e:
    logger.warning(f"⚠️ Erro ao carregar security: {e}")
    
    # Fallback básico
    class FallbackSecurityGuard:
        def __init__(self):
            self.logger = logger
        
        def validate_user_access(self, operation, resource=None):
            return True  # Permissivo em fallback
        
        def validate_input(self, input_data):
            return True  # Permissivo em fallback
        
        def sanitize_input(self, input_data):
            return str(input_data) if input_data else ""
        
        def get_security_info(self):
            return {'status': 'fallback', 'security_level': 'disabled'}
    
    # Atribuir classes fallback
    SecurityGuard = FallbackSecurityGuard
    
    # Funções fallback (sem tipos específicos para compatibilidade)
    def get_security_guard(): return SecurityGuard()
    
    # Re-atribuir funções para manter compatibilidade
    validate_user_access = lambda operation, resource=None: True
    validate_input = lambda input_data: True  
    sanitize_input = lambda input_data: str(input_data) if input_data else ""

# Funções de conveniência para segurança
def secure_validate(operation: str, resource: Optional[str] = None, input_data: Optional[str] = None) -> dict:
    """
    Validação completa de segurança em uma função.
    
    Args:
        operation: Operação a validar
        resource: Recurso sendo acessado
        input_data: Dados de entrada para sanitizar
        
    Returns:
        Resultado da validação de segurança
    """
    guard = get_security_guard()
    
    result = {
        'operation': operation,
        'resource': resource,
        'access_granted': guard.validate_user_access(operation, resource),
        'input_valid': True,
        'sanitized_input': input_data
    }
    
    if input_data:
        result['input_valid'] = guard.validate_input(input_data)
        result['sanitized_input'] = guard.sanitize_input(input_data)
    
    return result

def get_security_status() -> dict:
    """Retorna status completo do sistema de segurança"""
    guard = get_security_guard()
    return guard.get_security_info()

__all__ = [
    # Classe principal
    'SecurityGuard',
    'get_security_guard',
    
    # Funções básicas
    'validate_user_access',
    'validate_input',
    'sanitize_input',
    
    # Funções de conveniência
    'secure_validate',
    'get_security_status'
]
