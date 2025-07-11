#!/usr/bin/env python3
"""
FlaskContextWrapper - Abstração de contexto Flask
Extraído do processor_manager.py para melhor organização
"""

from app.claude_ai_novo.processors.base import BaseProcessor, logging
from app.claude_ai_novo.utils.base_classes import FLASK_AVAILABLE
from typing import Dict, Any, Optional

class FlaskContextWrapper(BaseProcessor):
    """Wrapper para abstrair contexto Flask"""
    
    def __init__(self):
        super().__init__()
        self._flask_available = FLASK_AVAILABLE
        self._app_config = {}
        self._db_session = None
        self._init_flask_context()
    
    def _init_flask_context(self):
        """Inicializa contexto Flask se disponível"""
        try:
            if self._flask_available:
                from flask import current_app
                self._app_config = current_app.config
                self.logger.debug("Contexto Flask inicializado")
            else:
                self._app_config = {}
                self.logger.warning("Flask não disponível - usando fallback")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar contexto Flask: {e}")
            self._flask_available = False
            self._app_config = {}
    
    def get_app_config(self) -> Dict[str, Any]:
        """Retorna configuração do app com fallback"""
        if self._flask_available:
            try:
                from flask import current_app
                return current_app.config
            except Exception as e:
                self.logger.warning(f"Erro ao acessar configuração Flask: {e}")
        
        return self._app_config
    
    def get_db_session(self) -> Optional[Any]:
        """Retorna sessão do banco com fallback"""
        if self._flask_available:
            try:
                from flask import current_app
                with current_app.app_context():
                    from app import db
                    return db.session
            except Exception as e:
                self.logger.warning(f"Erro ao acessar sessão DB: {e}")
        
        return None
    
    def is_flask_available(self) -> bool:
        """Verifica se Flask está disponível"""
        return self._flask_available
    
    def get_flask_context_info(self) -> Dict[str, Any]:
        """Retorna informações do contexto Flask"""
        info: Dict[str, Any] = {
            'flask_available': self._flask_available,
            'has_app_config': bool(self._app_config),
            'db_session_accessible': self.get_db_session() is not None
        }
        
        if self._flask_available:
            try:
                from flask import current_app, request
                # Adicionar campos Flask específicos
                info['app_name'] = current_app.name
                info['debug_mode'] = current_app.debug
                info['has_request_context'] = bool(request)
            except Exception as e:
                info['context_error'] = str(e)
        
        return info
    
    def execute_in_app_context(self, func, *args, **kwargs):
        """Executa função no contexto da aplicação Flask"""
        if not self._flask_available:
            self.logger.warning("Flask não disponível - executando sem contexto")
            return func(*args, **kwargs)
        
        try:
            from flask import current_app
            with current_app.app_context():
                return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Erro ao executar em contexto Flask: {e}")
            # Fallback - tentar executar sem contexto
            return func(*args, **kwargs)

# Instância global
_flask_context_wrapper = None

def get_flask_context_wrapper() -> FlaskContextWrapper:
    """Retorna instância singleton do FlaskContextWrapper"""
    global _flask_context_wrapper
    if _flask_context_wrapper is None:
        _flask_context_wrapper = FlaskContextWrapper()
    return _flask_context_wrapper 