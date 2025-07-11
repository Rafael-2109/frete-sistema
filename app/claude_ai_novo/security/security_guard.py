#!/usr/bin/env python3
"""
🔐 SECURITY GUARD - Guarda de Segurança
=======================================

Módulo responsável pela segurança e validação de operações no sistema.
Responsabilidade: PROTEGER o sistema contra operações não autorizadas.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import re
import hashlib

# Flask fallback para execução standalone
try:
    from app.claude_ai_novo.utils.flask_fallback import get_current_user
    from flask_login import current_user as flask_current_user
    current_user = get_current_user() or flask_current_user
except ImportError:
    from unittest.mock import Mock
    current_user = Mock()

# Configurar logger
logger = logging.getLogger(__name__)

class SecurityGuard:
    """
    Guarda de segurança para validação e proteção do sistema.
    
    Responsável por validar operações, verificar permissões e
    proteger contra acessos não autorizados.
    """
    
    def __init__(self):
        """Inicializa o guarda de segurança"""
        self.logger = logging.getLogger(__name__)
        self.blocked_patterns = [
            r'DROP\s+TABLE',
            r'DELETE\s+FROM.*WHERE\s+1=1',
            r'TRUNCATE\s+TABLE',
            r'ALTER\s+TABLE.*DROP',
            r'<script.*?>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
    def validate_user_access(self, operation: str, resource: Optional[str] = None) -> bool:
        """
        Valida se o usuário tem acesso a uma operação.
        
        Args:
            operation: Operação a ser realizada
            resource: Recurso sendo acessado (opcional)
            
        Returns:
            True se autorizado, False caso contrário
        """
        try:
            # Verificar se usuário está autenticado
            if not self._is_user_authenticated():
                self.logger.warning(f"🚫 Acesso negado - usuário não autenticado: {operation}")
                return False
            
            # Verificar operações administrativas
            if operation in ['admin', 'delete_all', 'system_reset']:
                if not self._is_user_admin():
                    self.logger.warning(f"🚫 Acesso negado - operação administrativa: {operation}")
                    return False
            
            # Verificar acesso a recursos específicos
            if resource and not self._validate_resource_access(resource):
                self.logger.warning(f"🚫 Acesso negado - recurso protegido: {resource}")
                return False
            
            self.logger.info(f"✅ Acesso autorizado: {operation} para {resource or 'recurso geral'}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de acesso: {e}")
            return False
    
    def validate_input(self, input_data: Union[str, Dict, List]) -> bool:
        """
        Valida entrada de dados contra padrões maliciosos.
        
        Args:
            input_data: Dados de entrada para validar
            
        Returns:
            True se dados são seguros, False caso contrário
        """
        try:
            # Converter para string se necessário
            if isinstance(input_data, (dict, list)):
                data_str = str(input_data)
            else:
                data_str = str(input_data)
            
            # Verificar padrões bloqueados
            for pattern in self.blocked_patterns:
                if re.search(pattern, data_str, re.IGNORECASE):
                    self.logger.warning(f"🚫 Entrada bloqueada - padrão suspeito: {pattern}")
                    return False
            
            # Verificar tamanho máximo
            if len(data_str) > 10000:  # 10KB máximo
                self.logger.warning(f"🚫 Entrada bloqueada - tamanho excessivo: {len(data_str)} chars")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de entrada: {e}")
            return False
    
    def validate_query(self, query: str) -> bool:
        """
        Valida consulta SQL contra injection.
        
        Args:
            query: Consulta SQL para validar
            
        Returns:
            True se consulta é segura, False caso contrário
        """
        try:
            if not query or not isinstance(query, str):
                return False
            
            # Padrões específicos para SQL injection
            sql_injection_patterns = [
                r';\s*DROP\s+TABLE',
                r';\s*DELETE\s+FROM',
                r';\s*INSERT\s+INTO',
                r';\s*UPDATE\s+.*SET',
                r'UNION\s+SELECT',
                r'--\s*$',
                r'/\*.*\*/',
                r"'\s*OR\s+'1'\s*=\s*'1",
                r'"\s*OR\s+"1"\s*=\s*"1',
            ]
            
            for pattern in sql_injection_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    self.logger.warning(f"🚫 Query bloqueada - SQL injection: {pattern}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de query: {e}")
            return False
    
    def sanitize_input(self, input_data: str) -> str:
        """
        Sanitiza entrada de dados removendo caracteres perigosos.
        
        Args:
            input_data: Dados para sanitizar
            
        Returns:
            Dados sanitizados
        """
        try:
            if not isinstance(input_data, str):
                input_data = str(input_data)
            
            # Remover caracteres perigosos
            sanitized = input_data
            
            # Remover scripts
            sanitized = re.sub(r'<script.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            
            # Remover eventos JavaScript
            sanitized = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
            
            # Remover javascript: URLs
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            
            # Limitar tamanho
            if len(sanitized) > 1000:
                sanitized = sanitized[:1000]
            
            return sanitized.strip()
            
        except Exception as e:
            self.logger.error(f"❌ Erro na sanitização: {e}")
            return ""
    
    def generate_token(self, data: str) -> str:
        """
        Gera token de segurança para dados.
        
        Args:
            data: Dados para gerar token
            
        Returns:
            Token de segurança
        """
        try:
            # Adicionar timestamp para uniqueness
            timestamp = str(datetime.now().timestamp())
            combined = f"{data}_{timestamp}"
            
            # Gerar hash SHA-256
            token = hashlib.sha256(combined.encode()).hexdigest()
            
            return token[:32]  # Primeiros 32 caracteres
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar token: {e}")
            return ""
    
    def validate_token(self, token: str, expected_data: Optional[str] = None) -> bool:
        """
        Valida token de segurança.
        
        Args:
            token: Token para validar
            expected_data: Dados esperados (opcional)
            
        Returns:
            True se token é válido, False caso contrário
        """
        try:
            # Verificar formato básico
            if not token or len(token) != 32:
                return False
            
            # Verificar se contém apenas caracteres hexadecimais
            if not re.match(r'^[a-f0-9]{32}$', token):
                return False
            
            # Se dados esperados fornecidos, validar
            if expected_data:
                # Gerar token esperado (simplificado)
                expected_token = self.generate_token(expected_data)
                return token == expected_token
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de token: {e}")
            return False
    
    def _is_user_authenticated(self) -> bool:
        """Verifica se usuário está autenticado"""
        try:
            return (
                current_user and 
                hasattr(current_user, 'is_authenticated') and 
                current_user.is_authenticated
            )
        except:
            return False
    
    def _is_user_admin(self) -> bool:
        """Verifica se usuário é administrador"""
        try:
            return (
                self._is_user_authenticated() and
                hasattr(current_user, 'perfil') and
                current_user.perfil in ['admin', 'administrador']
            )
        except:
            return False
    
    def _validate_resource_access(self, resource: str) -> bool:
        """Valida acesso a recurso específico"""
        try:
            # Recursos protegidos
            protected_resources = [
                'system_config',
                'user_management', 
                'database_admin',
                'security_logs'
            ]
            
            if resource in protected_resources:
                return self._is_user_admin()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de recurso: {e}")
            return False
    
    def get_security_info(self) -> Dict[str, Any]:
        """
        Retorna informações de segurança do sistema.
        
        Returns:
            Dict com informações de segurança
        """
        try:
            return {
                'user_authenticated': self._is_user_authenticated(),
                'user_admin': self._is_user_admin(),
                'blocked_patterns_count': len(self.blocked_patterns),
                'security_level': 'high',
                'last_check': datetime.now().isoformat(),
                'module': 'SecurityGuard',
                'version': '1.0.0'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter info de segurança: {e}")
            return {'error': str(e)}


# Instância global
_security_guard = None

def get_security_guard():
    """Retorna instância do SecurityGuard"""
    global _security_guard
    if _security_guard is None:
        _security_guard = SecurityGuard()
    return _security_guard

# Funções de conveniência
def validate_user_access(operation: str, resource: Optional[str] = None) -> bool:
    """Função de conveniência para validação de acesso"""
    return get_security_guard().validate_user_access(operation, resource)

def validate_input(input_data: Union[str, Dict, List]) -> bool:
    """Função de conveniência para validação de entrada"""
    return get_security_guard().validate_input(input_data)

def sanitize_input(input_data: str) -> str:
    """Função de conveniência para sanitização"""
    return get_security_guard().sanitize_input(input_data) 