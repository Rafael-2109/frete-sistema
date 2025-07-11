#!/usr/bin/env python3
"""
🔗 STANDALONE INTEGRATION - Integração Standalone
===============================================

Responsabilidade: INTEGRAR execução standalone (sem dependências Flask/web).
Renomeado: standalone_adapter.py → standalone_integration.py

Especializações:
- Execução independente de Flask
- Configuração via variáveis ambiente
- Fallbacks robustos
- Interface compatível com sistema modular
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class StandaloneContextManager:
    """Gerenciador de contexto para execução standalone."""
    
    def __init__(self):
        self.config = self._load_config()
        self.logger = logger
        self.initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração de variáveis de ambiente."""
        config = {
            'DEBUG': os.environ.get('DEBUG', 'False').lower() == 'true',
            'TESTING': os.environ.get('TESTING', 'False').lower() == 'true',
            'DATABASE_URL': os.environ.get('DATABASE_URL', ''),
            'SECRET_KEY': os.environ.get('SECRET_KEY', 'default-secret-key'),
            'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),
            'REDIS_URL': os.environ.get('REDIS_URL', '')
        }
        return config
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração."""
        return self.config.get(key, default)
    
    def is_available(self) -> bool:
        """Verifica se o manager está disponível."""
        return self.initialized

class StandaloneIntegration(StandaloneContextManager):
    """
    Integração para execução standalone sem dependências web.
    
    Responsabilidades:
    - Integrar sistema modular em modo standalone
    - Prover configuração via ambiente
    - Manter compatibilidade com código existente
    - Permitir execução sem Flask/web
    """
    
    def __init__(self):
        """Inicializa integração standalone."""
        super().__init__()
        self.components = {}
        self.status = "initialized"
        self._integration_manager = None
        self._external_api_integration = None
        
        logger.info("🔗 Standalone Integration inicializada")
    
    def _get_integration_manager(self):
        """Lazy loading do Integration Manager em modo standalone."""
        if self._integration_manager is None:
            try:
                from .integration_manager import IntegrationManager
                
                # Configurar sem Flask dependencies
                self._integration_manager = IntegrationManager(
                    claude_client=None  # Será configurado via external API
                )
                
            except Exception as e:
                logger.error(f"❌ Erro ao carregar Integration Manager standalone: {e}")
        
        return self._integration_manager
    
    def _get_external_api_integration(self):
        """Lazy loading do External API Integration."""
        if self._external_api_integration is None:
            try:
                from .external_api_integration import get_external_api_integration
                self._external_api_integration = get_external_api_integration()
            except Exception as e:
                logger.error(f"❌ Erro ao carregar External API Integration: {e}")
        
        return self._external_api_integration
    
    def initialize_system(self) -> Dict[str, Any]:
        """
        Inicializa sistema completo em modo standalone.
        
        Returns:
            Resultado da inicialização
        """
        try:
            logger.info("🚀 Inicializando sistema em modo standalone...")
            
            results = {
                'external_api': False,
                'integration_manager': False,
                'config_loaded': len(self.config) > 0
            }
            
            # Inicializar External API Integration
            external_api = self._get_external_api_integration()
            if external_api:
                init_result = external_api.initialize_complete_system()
                # Aguardar se for async
                if hasattr(init_result, '__await__'):
                    # Para modo standalone, executar de forma síncrona
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        init_result = loop.run_until_complete(init_result)
                    except RuntimeError:
                        init_result = asyncio.run(init_result)
                
                results['external_api'] = init_result.get('success', False)
            
            # Inicializar Integration Manager
            manager = self._get_integration_manager()
            if manager:
                results['integration_manager'] = True
            
            # Calcular score geral
            success_count = sum(1 for result in results.values() if result)
            total_checks = len(results)
            overall_score = success_count / total_checks
            
            self.status = "ready" if overall_score >= 0.5 else "limited"
            
            final_result = {
                'success': overall_score >= 0.5,
                'mode': 'standalone',
                'overall_score': overall_score,
                'status': self.status,
                'components': results,
                'initialized_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Standalone initialization - Score: {overall_score:.2f}")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização standalone: {e}")
            return {
                'success': False,
                'error': str(e),
                'mode': 'standalone',
                'initialized_at': datetime.now().isoformat()
            }
    
    def process_query(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Processa consulta em modo standalone.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            Resposta processada
        """
        if not query:
            return "Erro: Consulta vazia"
        
        try:
            # Garantir inicialização
            if self.status == "initialized":
                init_result = self.initialize_system()
                if not init_result.get('success'):
                    return f"Erro na inicialização: {init_result.get('error', 'Desconhecido')}"
            
            # Processar via External API Integration
            external_api = self._get_external_api_integration()
            if external_api:
                result = external_api.process_query(query, context)
                
                # Aguardar se for async
                if hasattr(result, '__await__'):
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        result = loop.run_until_complete(result)
                    except RuntimeError:
                        result = asyncio.run(result)
                
                if isinstance(result, str):
                    return result
            
            # Fallback simples
            return f"Processado em modo standalone: {query}"
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento standalone: {e}")
            return f"Erro no processamento: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status completo da integração standalone.
        
        Returns:
            Dict com status detalhado
        """
        try:
            status = {
                'integration': 'StandaloneIntegration',
                'mode': 'standalone',
                'initialized': self.initialized,
                'status': self.status,
                'flask_dependencies': False,
                'components': self.components,
                'config': {
                    'loaded': len(self.config) > 0,
                    'keys': list(self.config.keys()),
                    'anthropic_api_configured': bool(self.config.get('ANTHROPIC_API_KEY'))
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Status de componentes
            if self._external_api_integration:
                ext_status = self._external_api_integration.get_system_status()
                status['external_api_integration'] = ext_status
            
            if self._integration_manager:
                mgr_status = self._integration_manager.get_system_status()
                status['integration_manager'] = mgr_status
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {e}")
            return {
                'integration': 'StandaloneIntegration',
                'initialized': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check(self) -> bool:
        """
        Verifica se a integração está funcionando.
        
        Returns:
            True se saudável
        """
        try:
            # Verificar inicialização básica
            if not self.initialized:
                return False
            
            # Verificar se config está disponível
            if not self.config:
                logger.warning("⚠️ Config não disponível")
                return False
            
            # Verificar se status pode ser obtido
            test_status = self.get_status()
            if not isinstance(test_status, dict):
                return False
            
            logger.debug("✅ Standalone integration health check passou")
            return True
            
        except Exception as e:
            logger.error(f"❌ Health check falhou: {e}")
            return False
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa requisição de forma independente.
        
        Args:
            request_data: Dados da requisição
            
        Returns:
            Resultado do processamento
        """
        try:
            query = request_data.get('query', '')
            context = request_data.get('context', {})
            
            if query:
                response = self.process_query(query, context)
                return {
                    'success': True,
                    'response': response,
                    'processed_at': datetime.now().isoformat(),
                    'mode': 'standalone'
                }
            else:
                return {
                    'success': True,
                    'data': request_data,
                    'processed_at': datetime.now().isoformat(),
                    'mode': 'standalone'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar requisição: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_at': datetime.now().isoformat(),
                'mode': 'standalone'
            }


# Singleton para uso global
_standalone_integration = None

def get_standalone_integration() -> StandaloneIntegration:
    """
    Obtém instância global da integração standalone.
    
    Returns:
        Instância do StandaloneIntegration
    """
    global _standalone_integration
    if _standalone_integration is None:
        _standalone_integration = StandaloneIntegration()
    return _standalone_integration

# Função de compatibilidade
def get_standalone_adapter():
    """Compatibilidade - retorna standalone integration."""
    return get_standalone_integration()

def create_standalone_system() -> StandaloneIntegration:
    """
    Cria sistema standalone configurado.
    
    Returns:
        Sistema standalone pronto para uso
    """
    integration = get_standalone_integration()
    integration.initialize_system()
    return integration 