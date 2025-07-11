"""
🔧 CONFIG - Sistema de Configuração
===================================

Módulos responsáveis por gerenciamento de configurações do sistema.
"""

import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

# Importações com fallback robusto
try:
    from .advanced_config import AdvancedConfig, get_advanced_config
    _advanced_config_available = True
except ImportError as e:
    logger.warning(f"⚠️ AdvancedConfig não disponível: {e}")
    _advanced_config_available = False

try:
    from .system_config import SystemConfig, get_system_config
    _system_config_available = True
except ImportError as e:
    logger.warning(f"⚠️ SystemConfig não disponível: {e}")
    _system_config_available = False

# Instâncias globais
_advanced_config_instance = None
_system_config_instance = None

def get_advanced_config() -> Optional[object]:
    """
    Obtém instância da configuração avançada.
    
    Returns:
        Instância do AdvancedConfig ou None se não disponível
    """
    global _advanced_config_instance
    
    if not _advanced_config_available:
        logger.warning("⚠️ AdvancedConfig não está disponível")
        return None
    
    if _advanced_config_instance is None:
        try:
            from .advanced_config import AdvancedConfig
            _advanced_config_instance = AdvancedConfig()
            logger.info("✅ AdvancedConfig inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar AdvancedConfig: {e}")
            return None
    
    return _advanced_config_instance

def get_system_config() -> Optional[object]:
    """
    Obtém instância da configuração do sistema.
    
    Returns:
        Instância do SystemConfig ou None se não disponível
    """
    global _system_config_instance
    
    if not _system_config_available:
        logger.warning("⚠️ SystemConfig não está disponível")
        return None
    
    if _system_config_instance is None:
        try:
            from .system_config import SystemConfig
            _system_config_instance = SystemConfig()
            logger.info("✅ SystemConfig inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SystemConfig: {e}")
            return None
    
    return _system_config_instance

# COMPATIBILITY: ClaudeAIConfig para compatibilidade com código existente
class ClaudeAIConfig:
    """
    Classe de compatibilidade para configurações do Claude AI.
    
    Redireciona para o sistema de configuração apropriado.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config_cache = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração."""
        return get_config(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Define valor de configuração."""
        return set_config(key, value, persist=False)
    
    def reload(self) -> bool:
        """Recarrega configurações."""
        return reload_config()
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Obtém configurações específicas de IA."""
        return get_ai_config()
    
    def get_database_config(self) -> Dict[str, Any]:
        """Obtém configurações de banco de dados.""" 
        return get_database_config()
    
    def is_debug(self) -> bool:
        """Verifica se está em modo debug."""
        return is_debug_mode()
    
    def get_anthropic_api_key(self) -> Optional[str]:
        """
        Obtém a chave da API Anthropic.
        
        Returns:
            Chave da API ou None se não configurada
        """
        try:
            # Tentar obter de variável de ambiente primeiro
            import os
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                return api_key
            
            # Fallback para sistema de configuração
            api_key = get_config('ai.anthropic_api_key', None)
            if api_key:
                return api_key
            
            # Fallback para configuração Claude
            api_key = get_config('claude.api_key', None)
            if api_key:
                return api_key
            
            self.logger.warning("⚠️ ANTHROPIC_API_KEY não configurada - usando modo simulado")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter API key: {e}")
            return None

def get_config(key: str, default: Any = None, profile: Optional[str] = None) -> Any:
    """
    Obtém valor de configuração usando o sistema disponível.
    
    Args:
        key: Chave da configuração
        default: Valor padrão
        profile: Profile específico
        
    Returns:
        Valor da configuração ou padrão
    """
    try:
        # Tentar sistema de configuração primeiro (mais avançado)
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'get_config'):
            return system_config.get_config(key, default, profile)
        
        # Fallback para configuração avançada
        advanced_config = get_advanced_config()
        if advanced_config and hasattr(advanced_config, 'get'):
            return advanced_config.get(key, default)
        
        # Fallback final - configurações padrão embutidas
        default_configs = {
            'system.name': 'Claude AI Novo',
            'system.version': '2.0.0',
            'system.debug': False,
            'system.log_level': 'INFO',
            'ai.model': 'claude-sonnet-4',
            'ai.max_tokens': 4000,
            'ai.temperature': 0.7,
            'ai.timeout_seconds': 120,
            'database.connection_timeout': 30,
            'database.pool_size': 10,
            'database.retry_attempts': 3,
            'cache.enabled': True,
            'cache.ttl_minutes': 30,
            'cache.max_size': 1000
        }
        
        if key in default_configs:
            return default_configs[key]
        
        logger.debug(f"🔍 Configuração '{key}' não encontrada, usando padrão: {default}")
        return default
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter configuração '{key}': {e}")
        return default

def set_config(key: str, value: Any, profile: Optional[str] = None, persist: bool = True) -> bool:
    """
    Define valor de configuração.
    
    Args:
        key: Chave da configuração
        value: Valor a ser definido
        profile: Profile específico
        persist: Se deve persistir
        
    Returns:
        True se definido com sucesso
    """
    try:
        # Tentar sistema de configuração primeiro
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'set_config'):
            return system_config.set_config(key, value, profile, persist)
        
        # Fallback para configuração avançada
        advanced_config = get_advanced_config()
        if advanced_config and hasattr(advanced_config, 'set'):
            advanced_config.set(key, value)
            return True
        
        logger.warning(f"⚠️ Nenhum sistema de configuração disponível para definir '{key}'")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao definir configuração '{key}': {e}")
        return False

def get_profile_config(profile: str) -> Dict[str, Any]:
    """
    Obtém todas as configurações de um profile.
    
    Args:
        profile: Nome do profile
        
    Returns:
        Configurações do profile
    """
    try:
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'get_profile_config'):
            return system_config.get_profile_config(profile)
        
        return {}
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter configurações do profile '{profile}': {e}")
        return {}

def switch_profile(profile: str) -> bool:
    """
    Muda o profile ativo de configuração.
    
    Args:
        profile: Nome do profile
        
    Returns:
        True se mudança bem-sucedida
    """
    try:
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'switch_profile'):
            return system_config.switch_profile(profile)
        
        logger.warning(f"⚠️ Mudança de profile não suportada: {profile}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro ao mudar profile: {e}")
        return False

def reload_config(profile: Optional[str] = None) -> bool:
    """
    Recarrega configurações.
    
    Args:
        profile: Profile específico a recarregar
        
    Returns:
        True se recarregado com sucesso
    """
    try:
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'reload_config'):
            return system_config.reload_config(profile)
        
        # Reinicializar instâncias como fallback
        global _advanced_config_instance, _system_config_instance
        _advanced_config_instance = None
        _system_config_instance = None
        
        logger.info("🔄 Instâncias de configuração reinicializadas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao recarregar configurações: {e}")
        return False

def validate_configuration(profile: Optional[str] = None) -> Dict[str, Any]:
    """
    Valida configurações de um profile.
    
    Args:
        profile: Profile a validar
        
    Returns:
        Relatório de validação
    """
    try:
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'validate_configuration'):
            return system_config.validate_configuration(profile)
        
        return {
            'status': 'unavailable',
            'message': 'Sistema de validação não disponível'
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

def export_config(profile: Optional[str] = None, format: str = 'json') -> str:
    """
    Exporta configurações.
    
    Args:
        profile: Profile a exportar
        format: Formato de exportação
        
    Returns:
        String com configurações exportadas
    """
    try:
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'export_config'):
            return system_config.export_config(profile, format)
        
        # Fallback básico
        import json
        return json.dumps({
            'message': 'Sistema de exportação não disponível',
            'timestamp': str(__import__('datetime').datetime.now())
        }, indent=2)
        
    except Exception as e:
        logger.error(f"❌ Erro na exportação: {e}")
        return "{}"

def import_config(config_string: str, format: str = 'json', profile: Optional[str] = None) -> bool:
    """
    Importa configurações de string.
    
    Args:
        config_string: String com configurações
        format: Formato da string
        profile: Profile de destino
        
    Returns:
        True se importado com sucesso
    """
    try:
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'import_config'):
            return system_config.import_config(config_string, format, profile)
        
        logger.warning("⚠️ Sistema de importação não disponível")
        return False
        
    except Exception as e:
        logger.error(f"❌ Erro na importação: {e}")
        return False

def register_config_watcher(key_pattern: str, callback, name: Optional[str] = None) -> str:
    """
    Registra um watcher para mudanças de configuração.
    
    Args:
        key_pattern: Padrão de chave para observar
        callback: Função callback
        name: Nome do watcher
        
    Returns:
        ID do watcher registrado
    """
    try:
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'register_config_watcher'):
            return system_config.register_config_watcher(key_pattern, callback, name)
        
        logger.warning("⚠️ Sistema de watchers não disponível")
        return ""
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar watcher: {e}")
        return ""

def get_system_status() -> Dict[str, Any]:
    """
    Obtém status do sistema de configuração.
    
    Returns:
        Status detalhado
    """
    try:
        # Status do sistema principal
        system_status = {}
        system_config = get_system_config()
        if system_config and hasattr(system_config, 'get_system_status'):
            system_status = system_config.get_system_status()
        
        return {
            'advanced_config': {
                'available': _advanced_config_available,
                'initialized': _advanced_config_instance is not None
            },
            'system_config': {
                'available': _system_config_available,
                'initialized': _system_config_instance is not None
            },
            'total_components': 2,
            'active_components': sum([
                _advanced_config_available,
                _system_config_available
            ]),
            'primary_system': 'system' if _system_config_available else 'advanced' if _advanced_config_available else 'none',
            'system_details': system_status
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return {
            'error': str(e),
            'total_components': 2,
            'active_components': 0
        }

# Funções de conveniência para compatibilidade
def get_ai_config() -> Dict[str, Any]:
    """Obtém configurações de IA."""
    return {
        'model': get_config('ai.model', 'claude-sonnet-4'),
        'max_tokens': get_config('ai.max_tokens', 4000),
        'temperature': get_config('ai.temperature', 0.7),
        'timeout_seconds': get_config('ai.timeout_seconds', 120)
    }

def get_database_config() -> Dict[str, Any]:
    """Obtém configurações de banco de dados."""
    return {
        'connection_timeout': get_config('database.connection_timeout', 30),
        'pool_size': get_config('database.pool_size', 10),
        'retry_attempts': get_config('database.retry_attempts', 3)
    }

def get_cache_config() -> Dict[str, Any]:
    """Obtém configurações de cache."""
    return {
        'enabled': get_config('cache.enabled', True),
        'ttl_minutes': get_config('cache.ttl_minutes', 30),
        'max_size': get_config('cache.max_size', 1000)
    }

def is_debug_mode() -> bool:
    """Verifica se está em modo debug."""
    return get_config('system.debug', False)

def get_log_level() -> str:
    """Obtém nível de log configurado."""
    return get_config('system.log_level', 'INFO')

# Exportações
__all__ = [
    'ClaudeAIConfig',  # IMPORTANTE: Classe de compatibilidade
    'get_advanced_config',
    'get_system_config',
    'get_config',
    'set_config',
    'get_profile_config',
    'switch_profile',
    'reload_config',
    'validate_configuration',
    'export_config',
    'import_config',
    'register_config_watcher',
    'get_system_status',
    'get_ai_config',
    'get_database_config',
    'get_cache_config',
    'is_debug_mode',
    'get_log_level'
]

# Alias para compatibilidade com imports existentes
Config = ClaudeAIConfig
