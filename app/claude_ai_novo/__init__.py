"""
🚀 CLAUDE AI NOVO - Sistema Modular Integrado

Sistema de IA avançado completamente modularizado com arquitetura industrial:

MÓDULOS PRINCIPAIS:
- 🤖 Multi-Agent System: 6 agentes especializados
- 📊 Database scanners: 6 módulos de banco de dados  
- 🧠 Intelligence Learning: 5 módulos de aprendizado
- 🔍 Semantic Processing: Processamento semântico avançado
- 🎯 Suggestion Engine: Motor de sugestões inteligente
- 🔗 Integration Manager: Coordenação de todos os módulos

ARQUITETURA:
- Responsabilidade única por módulo
- Baixo acoplamento, alta coesão
- Escalabilidade e manutenibilidade
- Performance otimizada
- Compatibilidade total com versões anteriores
"""

import logging
from typing import Dict, List, Any, Optional
import asyncio
import sys
import os
import time

# Configurar logger do módulo
logger = logging.getLogger(__name__)

# DEBUG: Log de inicialização
_init_time = time.time()
logger.info(f"🚀 INICIALIZAÇÃO CLAUDE AI NOVO - PID: {os.getpid()} - Time: {_init_time}")

# Verificar se já foi inicializado
_already_initialized = False
if hasattr(sys.modules[__name__], '_initialized'):
    _already_initialized = sys.modules[__name__]._initialized
    logger.warning(f"⚠️ REINICIALIZAÇÃO DETECTADA - PID: {os.getpid()}")

sys.modules[__name__]._initialized = True

# Imports de compatibilidade (comentado para evitar imports circulares)
# from .claude_ai_modular import processar_consulta_modular, get_nlp_analyzer

# Função de compatibilidade local
def processar_consulta_modular(query: str, context: Optional[Dict] = None) -> str:
    """Função de compatibilidade local"""
    return f"Processando: {query}" if query else "Consulta vazia"

def get_nlp_analyzer():
    """Função de compatibilidade local"""
    return None

logger = logging.getLogger(__name__)


class ClaudeAINovo:
    """
    Classe principal do Claude AI Novo - Sistema Modular Integrado.
    
    Fornece interface unificada para todos os módulos especializados
    através do Integration Manager.
    """
    
    def __init__(self, claude_client=None, db_engine=None, db_session=None):
        """
        Inicializa o Claude AI Novo completo.
        
        Args:
            claude_client: Cliente do Claude API
            db_engine: Engine do banco de dados
            db_session: Sessão do banco de dados
        """
        self.claude_client = claude_client
        self.db_engine = db_engine
        self.db_session = db_session
        
        # Gerenciador de integração principal (import lazy)
        self.integration_manager = None
        
        # Estado do sistema
        self.system_ready = False
        self.initialization_result = None
        
        logger.info("🚀 Claude AI Novo inicializado - aguardando integração completa")
    
    def _get_integration_manager(self):
        """Import lazy do Integration Manager para evitar ciclos"""
        if self.integration_manager is None:
            from .integration.integration_manager import IntegrationManager
            self.integration_manager = IntegrationManager(
                claude_client=self.claude_client,
                db_engine=self.db_engine, 
                db_session=self.db_session
            )
        return self.integration_manager
    
    async def initialize_system(self) -> Dict[str, Any]:
        """
        Inicializa todo o sistema modular integrado.
        
        Returns:
            Dict com resultado da inicialização
        """
        logger.info("🔄 Iniciando sistema completo Claude AI Novo...")
        
        try:
            # Inicializar todos os módulos
            manager = self._get_integration_manager()
            self.initialization_result = await manager.initialize_all_modules()
            
            # Verificar se sistema está pronto
            self.system_ready = self.initialization_result.get('ready_for_operation', False)
            
            if self.system_ready:
                logger.info("✅ Claude AI Novo totalmente operacional!")
            else:
                logger.warning("⚠️ Claude AI Novo inicializado com limitações")
            
            return self.initialization_result
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização do sistema: {e}")
            return {
                'success': False,
                'error': str(e),
                'system_ready': False
            }
    
    async def process_query(self, query: Optional[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Processa uma consulta usando todo o sistema integrado.
        
        Args:
            query: Consulta do usuário (pode ser None)
            context: Contexto adicional
            
        Returns:
            Resposta processada pelo sistema completo
        """
        if not self.system_ready:
            return {
                'success': False,
                'error': 'Sistema não está pronto. Execute initialize_system() primeiro.',
                'fallback_response': 'Sistema em inicialização...'
            }
        
        manager = self._get_integration_manager()
        return await manager.process_unified_query(query, context)
    
    def get_module(self, module_name: str) -> Any:
        """
        Obtém acesso direto a um módulo específico.
        
        Args:
            module_name: Nome do módulo
            
        Returns:
            Instância do módulo ou None
        """
        manager = self._get_integration_manager()
        return manager.get_module(module_name)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Obtém status completo do sistema.
        
        Returns:
            Dict com status detalhado
        """
        manager = self._get_integration_manager()
        base_status = manager.get_system_status()
        
        base_status.update({
            'system_ready': self.system_ready,
            'claude_client_available': self.claude_client is not None,
            'database_available': self.db_engine is not None,
            'initialization_result': self.initialization_result
        })
        
        return base_status
    
    def get_available_modules(self) -> List[str]:
        """
        Lista todos os módulos disponíveis.
        
        Returns:
            Lista de nomes dos módulos
        """
        manager = self._get_integration_manager()
        return list(manager.modules.keys())
    
    # ===== MÉTODOS DE COMPATIBILIDADE =====
    
    async def processar_consulta(self, query: Optional[str], context: Optional[Dict] = None) -> str:
        """
        Método de compatibilidade para interface anterior.
        
        Args:
            query: Consulta do usuário (pode ser None)
            context: Contexto adicional
            
        Returns:
            Resposta como string
        """
        result = await self.process_query(query, context)
        
        if result.get('success'):
            # Extrair resposta principal
            agent_response = result.get('agent_response', {})
            if isinstance(agent_response, dict) and 'response' in agent_response:
                return agent_response['response']
            elif isinstance(agent_response, str):
                return agent_response
            else:
                return str(result.get('agent_response', 'Resposta não disponível'))
        else:
            return result.get('fallback_response', 'Erro no processamento')
    
    def process_query_sync(self, query: Optional[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Processa uma consulta de forma síncrona para uso em rotas Flask.
        
        Args:
            query: Consulta do usuário (pode ser None)
            context: Contexto adicional
            
        Returns:
            Resposta processada pelo sistema completo
        """
        try:
            # Executar de forma síncrona
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(self.process_query(query, context))
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento síncrono: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_response': 'Erro no processamento'
            }
    
    def processar_consulta_sync(self, query: Optional[str], context: Optional[Dict] = None) -> str:
        """
        Método síncrono de compatibilidade que retorna string.
        
        Args:
            query: Consulta do usuário (pode ser None)
            context: Contexto adicional
            
        Returns:
            Resposta como string
        """
        result = self.process_query_sync(query, context)
        
        if result.get('success'):
            # Extrair resposta principal
            agent_response = result.get('agent_response', {})
            if isinstance(agent_response, dict) and 'response' in agent_response:
                return agent_response['response']
            elif isinstance(agent_response, str):
                return agent_response
            else:
                return str(result.get('agent_response', 'Resposta não disponível'))
        else:
            return result.get('fallback_response', 'Erro no processamento')
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Método de compatibilidade para estatísticas.
        
        Returns:
            Dict com estatísticas do sistema
        """
        return self.get_system_status()


# Factory function para criação simplificada
async def create_claude_ai_novo(claude_client=None, db_engine=None, db_session=None, 
                               auto_initialize: bool = True) -> ClaudeAINovo:
    """
    Factory function para criar e inicializar Claude AI Novo.
    
    Args:
        claude_client: Cliente do Claude API
        db_engine: Engine do banco de dados
        db_session: Sessão do banco de dados
        auto_initialize: Se deve inicializar automaticamente
        
    Returns:
        Instância do Claude AI Novo pronta para uso
    """
    claude_ai = ClaudeAINovo(claude_client, db_engine, db_session)
    
    if auto_initialize:
        await claude_ai.initialize_system()
    
    return claude_ai


# ===== INSTÂNCIA GLOBAL (SINGLETON) =====

# Instância global para uso nas rotas
_claude_ai_instance = None

def get_claude_ai_instance():
    """
    Obtém instância global do Claude AI Novo.
    
    Esta função é usada pelas rotas para acessar o sistema.
    Cria a instância na primeira chamada (singleton pattern).
    
    Returns:
        Instância do Claude AI Novo configurada
    """
    global _claude_ai_instance
    
    if _claude_ai_instance is None:
        try:
            # Imports do sistema principal
            from app import db
            from app.claude_ai_novo.integration.external_api_integration import get_claude_client
            
            # Obter cliente do Claude
            claude_client = get_claude_client()
            
            # Criar instância
            _claude_ai_instance = ClaudeAINovo(
                claude_client=claude_client,
                db_engine=db.engine,
                db_session=db.session
            )
            
            # Tentar inicializar sistema de forma síncrona
            try:
                # Como as rotas são síncronas, vamos criar uma versão que funciona
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Executar inicialização
                initialization_result = loop.run_until_complete(_claude_ai_instance.initialize_system())
                logger.info(f"✅ Claude AI Novo inicializado: {initialization_result.get('success', False)}")
                
            except Exception as init_error:
                logger.warning(f"⚠️ Erro na inicialização completa: {init_error}")
                logger.info("💡 Sistema funcionará em modo básico")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar instância Claude AI Novo: {e}")
            # Retornar instância básica para evitar quebra total
            _claude_ai_instance = ClaudeAINovo()
    
    return _claude_ai_instance

def reset_claude_ai_instance():
    """
    Reseta a instância global (útil para testes).
    """
    global _claude_ai_instance
    _claude_ai_instance = None


# Exports principais
__all__ = [
    'ClaudeAINovo',
    'create_claude_ai_novo',
    'get_claude_ai_instance',  # ← ADICIONADO
    'reset_claude_ai_instance',  # ← ADICIONADO
    
    # Compatibilidade
    'processar_consulta_modular',
    'get_nlp_analyzer'
]

logger.info("✅ Sistema Claude AI Novo v1.0 - Totalmente Integrado")
