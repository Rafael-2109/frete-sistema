"""
🌐 EXTERNAL API INTEGRATION - Integração com APIs Externas
=========================================================

Responsabilidade: INTEGRAR com APIs e serviços externos (Claude, futuras APIs).
Consolida: claude_client.py + claude_integration.py

Especializações:
- Cliente Claude otimizado
- Integração completa Claude com sistema modular
- Suporte para futuras APIs externas
- Fallbacks e validação de conexão
"""

import os
import anthropic
from anthropic.types import MessageParam
import logging
import asyncio
from typing import Dict, Optional, Any, List, cast
from datetime import datetime
import json
try:
    from sqlalchemy import text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    text = None
    SQLALCHEMY_AVAILABLE = False

# Imports internos
from app.claude_ai_novo.utils.flask_fallback import get_db
from ..config.advanced_config import get_advanced_config_instance
from ..analyzers.performance_analyzer import classify_api_performance
from ..processors.response_processor import generate_api_fallback_response

logger = logging.getLogger(__name__)

class ExternalAPIClient:
    """
    Cliente base para APIs externas com configurações flexíveis.
    """
    
    def __init__(self, service_name: str, config_params: Optional[Dict] = None):
        """
        Inicializa cliente genérico para APIs externas.
        
        Args:
            service_name: Nome do serviço (claude, openai, etc.)
            config_params: Parâmetros específicos do serviço
        """
        self.service_name = service_name
        self.config_params = config_params or {}
        self.connected = False
        
        logger.info(f"🌐 Cliente {service_name} inicializado")
    
    def validate_connection(self) -> bool:
        """Valida conexão com API externa."""
        raise NotImplementedError("Implementar em subclasse")

class ClaudeAPIClient(ExternalAPIClient):
    """
    Cliente especializado para Claude API com configurações dinâmicas.
    """
    
    def __init__(self, api_key: str, config_params: Optional[Dict] = None):
        """
        Inicializa cliente Claude com configurações híbridas.
        
        Args:
            api_key: Chave da API Anthropic
            config_params: Parâmetros específicos (opcional)
        """
        super().__init__("claude", {})
        
        # Cliente Anthropic
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.api_key = api_key
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar cliente Claude: {e}")
            self.client = None
            self.api_key = None
        
        # Configurações híbridas
        if config_params:
            # Parâmetros diretos (para flexibilidade máxima)
            self.model = config_params.get('model', 'claude-sonnet-4-20250514')
            self.max_tokens = config_params.get('max_tokens', 8192)
            self.temperature = config_params.get('temperature', 0.7)
            self.top_p = config_params.get('top_p', 0.95)
        else:
            # Configuração padrão do sistema híbrido
            config = get_advanced_config_instance()
            params = config.get_claude_params()
            self.model = params['model']
            self.max_tokens = params['max_tokens']
            self.temperature = params['temperature']
            self.top_p = params['top_p']
    
    @classmethod
    def from_environment(cls):
        """Cria cliente usando variável de ambiente com lazy loading."""
        # Tentar obter API key de múltiplas fontes
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Se não encontrou, tentar carregar .env
        if not api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv('ANTHROPIC_API_KEY')
            except ImportError:
                pass
        
        # Se ainda não encontrou, tentar da configuração
        if not api_key:
            try:
                from ..config.basic_config import ClaudeAIConfig
                api_key = ClaudeAIConfig.get_anthropic_api_key()
            except ImportError:
                pass
                
        if not api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY não encontrada - tentando fallback")
            raise ValueError("ANTHROPIC_API_KEY não configurada em nenhuma fonte")
            
        return cls(api_key)
    
    @classmethod
    def from_mode(cls, api_key: str, mode: str = "balanced"):
        """
        Cria cliente usando modo específico via configuração híbrida.
        
        Args:
            api_key: Chave da API
            mode: precision, creative, balanced
        """
        config = get_advanced_config_instance()
        params = config.get_claude_params(mode)
        return cls(api_key, params)
    
    def send_message(self, messages: List[Dict], system_prompt: str = "") -> str:
        """Envia mensagem para Claude e retorna resposta."""
        if not self.client:
            raise ConnectionError("Cliente Claude não inicializado")
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=cast(List[MessageParam], messages)
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"❌ Erro ao comunicar com Claude: {e}")
            raise
    
    def validate_connection(self) -> bool:
        """Valida conexão com Claude API."""
        if not self.client:
            return False
        
        try:
            test_response = self.send_message([
                {"role": "user", "content": "Hi"}
            ])
            self.connected = len(test_response) > 0
            return self.connected
        except Exception as e:
            logger.debug(f"⚠️ Falha na validação Claude: {e}")
            self.connected = False
            return False
    
    def get_current_config(self) -> Dict:
        """Retorna configuração atual do cliente."""
        return {
            'service': self.service_name,
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': getattr(self, 'top_p', 0.95),
            'connected': self.connected
        }
    
    def update_temperature(self, new_temperature: float):
        """Atualiza temperature dinamicamente."""
        self.temperature = max(0.0, min(1.0, new_temperature))
    
    def switch_mode(self, mode: str):
        """Muda modo operacional (precision, creative, balanced)."""
        mode_configs = {
            "precision": {"temperature": 0.1},
            "creative": {"temperature": 0.9},
            "balanced": {"temperature": 0.7}
        }
        
        if mode in mode_configs:
            config = mode_configs[mode]
            self.temperature = config["temperature"]
            logger.info(f"🔄 Claude modo alterado para: {mode}")

class ExternalAPIIntegration:
    """
    Integração principal com APIs externas, especialmente Claude.
    
    Responsabilidades:
    - Gerenciar conexões com APIs externas
    - Coordenar sistema completo quando disponível
    - Prover fallback para Claude direto
    """
    
    @property
    def db(self):
        """Obtém db com fallback"""
        return get_db()
    
    def __init__(self):
        """Inicializa a integração com APIs externas."""
        # Configuração Claude
        self.claude_client = None
        self.claude_connected = False
        
        # Estado do sistema
        self.integration_manager = None
        self.system_ready = False
        
        # Cache e persistência já não precisa mais
        
        # Inicialização
        self._initialize_clients()
        
        logger.info("🌐 External API Integration inicializada")
    
    def _initialize_clients(self):
        """Inicializa clientes de APIs externas."""
        # Inicializar Claude
        try:
            self.claude_client = ClaudeAPIClient.from_environment()
            self.claude_connected = self.claude_client.validate_connection()
            
            if self.claude_connected:
                logger.info("🚀 Claude API conectada com sucesso!")
            else:
                logger.warning("⚠️ Claude API não conectada - modo fallback")
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar Claude: {e}")
            self.claude_client = None
            self.claude_connected = False
    
    def _get_integration_manager(self):
        """Lazy loading do Integration Manager."""
        if self.integration_manager is None:
            try:
                from .integration_manager import IntegrationManager
                self.integration_manager = IntegrationManager(
                    claude_client=self.claude_client.client if self.claude_client else None,
                    db_engine=self.db.engine,
                    db_session=self.db.session
                )
            except Exception as e:
                logger.error(f"❌ Erro ao carregar Integration Manager: {e}")
        
        return self.integration_manager
    
    async def initialize_complete_system(self) -> Dict[str, Any]:
        """
        Inicializa sistema completo com todas as APIs.
        
        Returns:
            Resultado da inicialização
        """
        start_time = datetime.now()
        logger.info("🚀 Inicializando sistema completo de APIs externas...")
        
        try:
            results = {
                'claude_api': self._validate_claude_connection(),
                'integration_manager': False,
                'system_modules': 0,
                'active_modules': 0
            }
            
            # Inicializar Integration Manager se Claude disponível
            if self.claude_connected:
                manager = self._get_integration_manager()
                if manager:
                    try:
                        init_result = await manager.initialize_all_modules()
                        results['integration_manager'] = init_result.get('success', False)
                        
                        if results['integration_manager']:
                            status = manager.get_system_status()
                            results['system_modules'] = status.get('total_modules', 0)
                            results['active_modules'] = status.get('active_modules', 0)
                    except Exception as e:
                        logger.error(f"❌ Erro na inicialização do manager: {e}")
            
            # Calcular score geral
            api_score = 1.0 if results['claude_api'] else 0.0
            manager_score = 1.0 if results['integration_manager'] else 0.0
            
            overall_score = (api_score + manager_score) / 2
            self.system_ready = overall_score >= 0.5
            
            initialization_time = (datetime.now() - start_time).total_seconds()
            
            final_result = {
                'success': self.system_ready,
                'overall_score': overall_score,
                'initialization_time': initialization_time,
                'apis_connected': {
                    'claude': results['claude_api']
                },
                'integration_manager_ready': results['integration_manager'],
                'total_modules': results['system_modules'],
                'active_modules': results['active_modules'],
                'performance_class': self._classify_performance(overall_score)
            }
            
            logger.info(f"✅ Inicialização externa concluída - Score: {overall_score:.2f}")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização externa: {e}")
            return {
                'success': False,
                'error': str(e),
                'initialization_time': (datetime.now() - start_time).total_seconds()
            }
    
    async def process_query(self, query: str, user_context: Optional[Dict] = None) -> str:
        """
        Processa consulta usando APIs externas e sistema modular.
        
        Args:
            query: Consulta do usuário
            user_context: Contexto do usuário
            
        Returns:
            Resposta processada
        """
        if not query or not isinstance(query, str):
            return self._generate_fallback_response(query or "Consulta vazia", "Query inválida")
        
        # Garantir inicialização
        if not self.system_ready:
            init_result = await self.initialize_complete_system()
            if not init_result.get('success'):
                return self._generate_fallback_response(query, "Sistema não inicializado")
        
        try:
            # Rota 1: Sistema completo (Claude + Integration Manager)
            if self.claude_connected and self.integration_manager:
                return await self._process_with_full_system(query, user_context)
            
            # Rota 2: Apenas Claude direto
            elif self.claude_connected:
                return await self._process_with_claude_only(query, user_context)
            
            # Rota 3: Fallback sem APIs externas
            else:
                return self._generate_fallback_response(query, "APIs externas indisponíveis")
                
        except Exception as e:
            logger.error(f"❌ Erro no processamento de query: {e}")
            return self._generate_fallback_response(query, f"Erro interno: {e}")
    
    async def _process_with_full_system(self, query: str, user_context: Optional[Dict] = None) -> str:
        """Processa com sistema completo (Claude + Integration Manager)."""
        try:
            manager = self._get_integration_manager()
            result = await manager.process_unified_query(query, user_context)
            
            if result and result.get('success'):
                response = result.get('agent_response', {})
                
                # Extrair resposta
                if isinstance(response, dict):
                    return response.get('response', str(response))
                else:
                    return str(response)
            else:
                # Fallback para Claude direto
                return await self._process_with_claude_only(query, user_context)
                
        except Exception as e:
            logger.error(f"❌ Erro no sistema completo: {e}")
            return await self._process_with_claude_only(query, user_context)
    
    async def _process_with_claude_only(self, query: str, user_context: Optional[Dict] = None) -> str:
        """Processa apenas com Claude direto."""
        if not self.claude_client:
            return self._generate_fallback_response(query, "Claude não disponível")
        
        try:
            # Sistema prompt básico
            system_prompt = "Você é um assistente especializado em logística e transporte."
            
            # Incluir contexto se disponível
            if user_context:
                context_str = json.dumps(user_context, indent=2)
                system_prompt += f"\n\nContexto do usuário:\n{context_str}"
            
            # Mensagem para Claude
            messages = [{"role": "user", "content": query}]
            
            response = self.claude_client.send_message(messages, system_prompt)
            return response
            
        except Exception as e:
            logger.error(f"❌ Erro no Claude direto: {e}")
            return self._generate_fallback_response(query, f"Erro Claude: {e}")
    
    def _validate_claude_connection(self) -> bool:
        """Valida conexão Claude."""
        if self.claude_client:
            return self.claude_client.validate_connection()
        return False
    
    def _classify_performance(self, score: float) -> str:
        """Classifica performance do sistema usando analyzer especializado."""
        return classify_api_performance(score)
    
    def _generate_fallback_response(self, query: str, error: str) -> str:
        """Gera resposta de fallback usando processor especializado."""
        context = {
            'claude_connected': self.claude_connected,
            'integration_manager': self.integration_manager is not None
        }
        return generate_api_fallback_response(query, error, context)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema."""
        status = {
            'timestamp': datetime.now().isoformat(),
            'system_ready': self.system_ready,
            'external_apis': {
                'claude': {
                    'connected': self.claude_connected,
                    'config': self.claude_client.get_current_config() if self.claude_client else None
                }
            },
            'integration_manager': {
                'available': self.integration_manager is not None,
                'status': None
            }
        }
        
        # Status do Integration Manager
        if self.integration_manager:
            try:
                manager_status = self.integration_manager.get_system_status()
                status['integration_manager']['status'] = manager_status
            except Exception as e:
                status['integration_manager']['error'] = str(e)
        
        return status


# Instâncias globais para conveniência
_external_api_integration = None
_claude_client = None

def get_external_api_integration() -> ExternalAPIIntegration:
    """
    Retorna instância global do External API Integration.
    
    Returns:
        Instância do ExternalAPIIntegration
    """
    global _external_api_integration
    if _external_api_integration is None:
        _external_api_integration = ExternalAPIIntegration()
    return _external_api_integration

def get_claude_client() -> Optional[ClaudeAPIClient]:
    """
    Retorna cliente Claude configurado.
    
    Returns:
        Cliente Claude ou None se não disponível
    """
    global _claude_client
    if _claude_client is None:
        try:
            _claude_client = ClaudeAPIClient.from_environment()
        except Exception as e:
            logger.warning(f"⚠️ Claude client não disponível: {e}")
            _claude_client = None
    return _claude_client

def create_claude_client(api_key: str, mode: str = "balanced") -> ClaudeAPIClient:
    """
    Cria novo cliente Claude com configurações específicas usando sistema híbrido.
    
    Args:
        api_key: Chave da API
        mode: Modo operacional (precision, creative, balanced)
        
    Returns:
        Cliente Claude configurado
    """
    return ClaudeAPIClient.from_mode(api_key, mode)

async def process_with_external_apis(query: str, user_context: Optional[Dict] = None) -> str:
    """
    Função de conveniência para processar consulta com APIs externas.
    
    Args:
        query: Consulta do usuário
        user_context: Contexto do usuário
        
    Returns:
        Resposta processada
    """
    integration = get_external_api_integration()
    return await integration.process_query(query, user_context)

# Compatibilidade com código existente
def get_claude_integration():
    """Compatibilidade - retorna integração externa."""
    return get_external_api_integration()

def processar_com_claude_real(consulta: str, user_context: Optional[Dict] = None) -> str:
    """Compatibilidade - processa consulta de forma síncrona."""
    integration = get_external_api_integration()
    
    # Para compatibilidade síncrona
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            integration.process_query(consulta, user_context)
        )
    except RuntimeError:
        # Se não há loop, criar um novo
        return asyncio.run(
            integration.process_query(consulta, user_context)
        ) 