"""
🧠 CONFIGURAÇÃO AVANÇADA DO CLAUDE AI
Herda de basic_config.py e adiciona recursos avançados
Integração com SystemConfig para configurações dinâmicas
"""

from .basic_config import ClaudeAIConfig
from .system_config import get_system_config

# 🚀 CONFIGURAÇÕES AVANÇADAS (estendem as básicas)
CLAUDE_ADVANCED_CONFIG = {
    # Herda parâmetros básicos de ClaudeAIConfig
    "max_tokens": 8192,              # Confirmado de ClaudeAIConfig
    "max_output_tokens": 8192,       # Extensão: Saída completa
    "temperature_precision": 0.1,    # Extensão: Modo precisão
    "temperature_creative": 0.9,     # Extensão: Modo criativo
    "top_p": 0.95,                   # Extensão: Criatividade controlada
    
    # Capacidades expandidas
    "max_file_size_mb": 50,
    "max_lines_read": 50000,
    "max_search_results": 5000,
    "max_variables_extract": 500,
    
    # Recursos avançados
    "deep_analysis": True,
    "context_window": 200000,
    "multi_file_analysis": True,
    "recursive_scanning": True,
    "unlimited_sql_results": True,
    "batch_processing": True,
    "parallel_analysis": True,
    "smart_caching": True,
    "auto_backup": True,
    "multi_file_generation": True,
    "advanced_refactoring": True,
    "intelligent_imports": True,
}

class AdvancedConfig(ClaudeAIConfig):
    """
    Configuração avançada que herda de ClaudeAIConfig e usa SystemConfig.
    
    Resolve conflitos e adiciona funcionalidades especializadas.
    """
    
    def __init__(self, claude_client=None, db_engine=None, db_session=None):
        """Inicializa configuração avançada"""
        
        # Componentes externos
        self.claude_client = claude_client
        self.db_engine = db_engine
        self.db_session = db_session
        
        # Sistema de configuração dinâmica
        self.system_config = get_system_config()
        
        # Estado avançado
        self.unlimited_mode = True
        self.initialized = True
    
    def get_temperature(self, mode="balanced") -> float:
        """
        Retorna temperature baseado no modo usando SystemConfig.
        
        Args:
            mode: "balanced" (0.7), "precision" (0.1), "creative" (0.9)
        """
        return self.system_config.get_config(f'claude_api.temperature_{mode}', 0.7)
    
    def get_claude_params(self, mode="balanced") -> dict:
        """
        Retorna parâmetros Claude com modo específico usando SystemConfig.
        
        Args:
            mode: Modo de operação
        """
        return {
            'model': self.system_config.get_config('claude_api.model', 'claude-sonnet-4-20250514'),
            'max_tokens': self.system_config.get_config('claude_api.max_tokens', 8192),
            'temperature': self.get_temperature(mode),
            'top_p': self.system_config.get_config('claude_api.top_p', 0.95),
            'timeout_seconds': self.system_config.get_config('claude_api.timeout_seconds', 120)
        }
    
    def create_claude_client(self, api_key: str, mode: str = "balanced"):
        """Factory method usando configurações dinâmicas do SystemConfig"""
        from ..integration.external_api_integration import ClaudeAPIClient
        params = self.get_claude_params(mode)
        return ClaudeAPIClient(api_key, params)
    
    def get_config(self) -> dict:
        """Retorna configuração completa mesclando SystemConfig e configurações locais"""
        basic_config = super().to_dict()
        system_claude_config = self.system_config.get_profile_config(self.system_config.active_profile)
        
        return {
            **basic_config,
            **CLAUDE_ADVANCED_CONFIG,
            **system_claude_config.get('claude_api', {}),
            "unlimited_mode": self.unlimited_mode,
            "initialized": self.initialized,
            "active_profile": self.system_config.active_profile
        }

def get_advanced_config():
    """Retorna configuração avançada completa"""
    return {**CLAUDE_ADVANCED_CONFIG}

def is_unlimited_mode():
    """Verifica se modo ilimitado está ativo"""
    return True

# Instância global
_advanced_config_instance = None

def get_advanced_config_instance():
    """Obtém instância global da configuração avançada."""
    global _advanced_config_instance
    if _advanced_config_instance is None:
        _advanced_config_instance = AdvancedConfig()
    return _advanced_config_instance
