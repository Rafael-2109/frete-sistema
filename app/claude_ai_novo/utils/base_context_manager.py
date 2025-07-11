#!/usr/bin/env python3
"""
Base Context Manager - Classe base para managers standalones
==========================================================

Classe base standalone sem dependências Flask para todos os managers
que precisam de contexto básico.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseContextManager:
    """
    Manager base standalone sem dependências externas
    
    Fornece funcionalidades básicas de contexto e configuração
    para todos os managers filhos.
    """
    
    def __init__(self):
        """Inicializa o manager base"""
        self._config = {}
        self._initialized = False
    
    def _get_config(self, key: str, default: Any = None) -> Any:
        """
        Retorna configuração com fallback
        
        Args:
            key: Chave da configuração
            default: Valor padrão se chave não existir
            
        Returns:
            Valor da configuração ou default
        """
        return self._config.get(key, default)
    
    def _set_config(self, key: str, value: Any) -> None:
        """
        Define configuração
        
        Args:
            key: Chave da configuração
            value: Valor a ser definido
        """
        self._config[key] = value
    
    def is_available(self) -> bool:
        """
        Verifica se o manager está disponível
        
        Returns:
            True se inicializado e disponível
        """
        return self._initialized
    
    def get_config_dict(self) -> Dict[str, Any]:
        """
        Retorna dicionário completo de configuração
        
        Returns:
            Dict com todas as configurações
        """
        return self._config.copy()
    
    def set_initialized(self, status: bool = True) -> None:
        """
        Define status de inicialização
        
        Args:
            status: True se inicializado com sucesso
        """
        self._initialized = status
    
    def clear_config(self) -> None:
        """Limpa todas as configurações"""
        self._config.clear()
    
    def update_config(self, config_dict: Dict[str, Any]) -> None:
        """
        Atualiza configurações em lote
        
        Args:
            config_dict: Dict com configurações a serem atualizadas
        """
        self._config.update(config_dict)
    
    def __repr__(self) -> str:
        """Representação do manager"""
        return f"<{self.__class__.__name__} initialized={self._initialized}>"

# Função de conveniência para criar instância
def create_base_context_manager() -> BaseContextManager:
    """
    Cria nova instância de BaseContextManager
    
    Returns:
        Nova instância configurada
    """
    return BaseContextManager()

# Exportações
__all__ = [
    'BaseContextManager',
    'create_base_context_manager'
] 