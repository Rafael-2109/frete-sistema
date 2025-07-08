"""
🚀 CLAUDE AI NOVO - Sistema Modular Integrado

Sistema de IA avançado completamente modularizado com arquitetura industrial:

MÓDULOS PRINCIPAIS:
- 🤖 Multi-Agent System: 6 agentes especializados
- 📊 Database Readers: 6 módulos de banco de dados  
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

# Imports de compatibilidade (somente funções)
from .claude_ai_modular import processar_consulta_modular, get_nlp_analyzer

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
            from .integration_manager import IntegrationManager
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


# Exports principais
__all__ = [
    'ClaudeAINovo',
    'create_claude_ai_novo',
    
    # Compatibilidade
    'processar_consulta_modular',
    'get_nlp_analyzer'
]
