#!/usr/bin/env python3
"""
🧠 MEMORY MANAGER - Gerenciador de Memória
==========================================

Módulo responsável por gerenciar todos os tipos de memória do sistema.
Responsabilidade: COORDENAR todos os memorizadores.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Imports dos memorizadores
from .context_memory import ContextMemory, get_context_memory
from .conversation_memory import ConversationMemory, get_conversation_memory
from .system_memory import SystemMemory, get_system_memory
from .knowledge_memory import KnowledgeMemory, get_knowledge_memory

# Configurar logger
logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Gerenciador central de memória do sistema.
    
    Coordena todos os tipos de memória: contexto, conversa, sistema e conhecimento.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de memória"""
        self.logger = logging.getLogger(__name__)
        self.context_memory = get_context_memory()
        self.conversation_memory = get_conversation_memory()
        self.system_memory = get_system_memory()
        self.knowledge_memory = KnowledgeMemory()
        
        # Registrar inicialização
        self.logger.info("🧠 MemoryManager inicializado")
        
    def store_conversation_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """
        Armazena contexto de conversa.
        
        Args:
            session_id: ID da sessão
            context: Contexto da conversa
            
        Returns:
            True se armazenado com sucesso
        """
        try:
            return self.context_memory.store_context(session_id, context)
        except Exception as e:
            self.logger.error(f"❌ Erro ao armazenar contexto de conversa: {e}")
            return False
    
    def retrieve_conversation_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera contexto de conversa.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Contexto da conversa ou None
        """
        try:
            return self.context_memory.retrieve_context(session_id)
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar contexto de conversa: {e}")
            return None
    
    def store_system_configuration(self, config_key: str, config_value: Any) -> bool:
        """
        Armazena configuração do sistema.
        
        Args:
            config_key: Chave da configuração
            config_value: Valor da configuração
            
        Returns:
            True se armazenado com sucesso
        """
        try:
            return self.system_memory.store_system_config(config_key, config_value)
        except Exception as e:
            self.logger.error(f"❌ Erro ao armazenar configuração do sistema: {e}")
            return False
    
    def retrieve_system_configuration(self, config_key: str) -> Optional[Any]:
        """
        Recupera configuração do sistema.
        
        Args:
            config_key: Chave da configuração
            
        Returns:
            Valor da configuração ou None
        """
        try:
            return self.system_memory.retrieve_system_config(config_key)
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar configuração do sistema: {e}")
            return None
    
    def learn_client_mapping(self, query: str, client: str) -> Optional[Dict[str, Any]]:
        """
        Aprende mapeamento de cliente através do knowledge manager.
        
        Args:
            query: Consulta original
            client: Nome do cliente
            
        Returns:
            Resultado do aprendizado ou None
        """
        try:
            return self.knowledge_memory.aprender_mapeamento_cliente(query, client)
        except Exception as e:
            self.logger.error(f"❌ Erro ao aprender mapeamento de cliente: {e}")
            return None
    
    def discover_business_group(self, interpretation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Descobre grupo empresarial através do knowledge memory.
        
        Args:
            interpretation: Interpretação com dados do grupo
            
        Returns:
            Grupo descoberto ou None
        """
        try:
            return self.knowledge_memory.descobrir_grupo_empresarial(interpretation)
        except Exception as e:
            self.logger.error(f"❌ Erro ao descobrir grupo empresarial: {e}")
            return None
    
    def add_conversation_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Adiciona mensagem à conversa.
        
        Args:
            session_id: ID da sessão
            message: Mensagem para adicionar
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            return self.context_memory.add_message(session_id, message)
        except Exception as e:
            self.logger.error(f"❌ Erro ao adicionar mensagem à conversa: {e}")
            return False
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recupera histórico de conversa.
        
        Args:
            session_id: ID da sessão
            limit: Limite de mensagens
            
        Returns:
            Lista de mensagens
        """
        try:
            return self.context_memory.get_conversation_history(session_id, limit)
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar histórico de conversa: {e}")
            return []
    
    def start_conversation(self, session_id: str, initial_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inicia nova conversa usando conversation_memory.
        
        Args:
            session_id: ID da sessão
            initial_context: Contexto inicial
            
        Returns:
            True se iniciado com sucesso
        """
        try:
            return self.conversation_memory.start_conversation(session_id, initial_context or {})
        except Exception as e:
            self.logger.error(f"❌ Erro ao iniciar conversa: {e}")
            return False
    
    def end_conversation(self, session_id: str) -> bool:
        """
        Finaliza conversa usando conversation_memory.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se finalizado com sucesso
        """
        try:
            return self.conversation_memory.end_conversation(session_id)
        except Exception as e:
            self.logger.error(f"❌ Erro ao finalizar conversa: {e}")
            return False
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna resumo da conversa usando conversation_memory.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Resumo da conversa
        """
        try:
            return self.conversation_memory.get_conversation_summary(session_id)
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter resumo da conversa: {e}")
            return {'error': str(e)}
    
    def record_performance_metric(self, metric_name: str, value: Union[int, float], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Registra métrica de desempenho.
        
        Args:
            metric_name: Nome da métrica
            value: Valor da métrica
            metadata: Metadados adicionais
            
        Returns:
            True se registrado com sucesso
        """
        try:
            return self.system_memory.store_performance_metric(metric_name, value, metadata or {})
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar métrica de desempenho: {e}")
            return False
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        Retorna visão geral de toda a memória do sistema.
        
        Returns:
            Dict com informações gerais
        """
        try:
            overview = {
                'memory_manager': {
                    'initialized': True,
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0.0'
                },
                'context_memory': self.context_memory.get_memory_stats() if self.context_memory else {'error': 'not_available'},
                'conversation_memory': {'available': bool(self.conversation_memory)},
                'system_memory': self.system_memory.get_system_overview() if self.system_memory else {'error': 'not_available'},
                'knowledge_memory': self.knowledge_memory.obter_estatisticas_aprendizado() if self.knowledge_memory else {'error': 'not_available'}
            }
            
            return overview
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter visão geral do sistema: {e}")
            return {'error': str(e)}
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Limpa dados expirados de todos os memorizadores.
        
        Returns:
            Dict com contadores de limpeza
        """
        try:
            cleanup_results = {}
            
            # Limpar contexto
            if self.context_memory:
                cleanup_results['context_memory'] = self.context_memory.cleanup_expired_contexts()
            
            # Limpar sistema
            if self.system_memory:
                cleanup_results['system_memory'] = self.system_memory.cleanup_expired_data()
            
            # Knowledge memory não tem método cleanup específico
            cleanup_results['knowledge_memory'] = 0
            
            # Conversation memory não tem método cleanup específico
            cleanup_results['conversation_memory'] = 0
            
            total_cleaned = sum(cleanup_results.values())
            self.logger.info(f"🧹 Limpeza completa realizada: {total_cleaned} itens removidos")
            
            return cleanup_results
            
        except Exception as e:
            self.logger.error(f"❌ Erro na limpeza de dados expirados: {e}")
            return {'error': -1}
    
    def clear_all_context(self, session_id: str) -> bool:
        """
        Limpa todo o contexto de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se limpo com sucesso
        """
        try:
            return self.context_memory.clear_context(session_id)
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar contexto: {e}")
            return False
    
    def get_active_sessions(self) -> List[str]:
        """
        Retorna lista de sessões ativas.
        
        Returns:
            Lista de IDs de sessões ativas
        """
        try:
            return self.context_memory.get_active_sessions()
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter sessões ativas: {e}")
            return []
    
    def get_memory_health(self) -> Dict[str, Any]:
        """
        Retorna status de saúde da memória.
        
        Returns:
            Dict com status de saúde
        """
        try:
            health = {
                'overall_status': 'healthy',
                'components': {
                    'context_memory': 'available' if self.context_memory else 'unavailable',
                    'conversation_memory': 'available' if self.conversation_memory else 'unavailable',
                    'system_memory': 'available' if self.system_memory else 'unavailable',
                    'knowledge_memory': 'available' if self.knowledge_memory else 'unavailable'
                },
                'active_sessions': len(self.get_active_sessions()),
                'last_check': datetime.now().isoformat()
            }
            
            # Verificar se algum componente está indisponível
            unavailable_components = [k for k, v in health['components'].items() if v == 'unavailable']
            if unavailable_components:
                health['overall_status'] = 'degraded'
                health['issues'] = f"Componentes indisponíveis: {', '.join(unavailable_components)}"
            
            return health
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar saúde da memória: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém contexto completo da sessão para o workflow.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Contexto completo incluindo histórico e preferências
        """
        try:
            context: Dict[str, Any] = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # Histórico de conversação
            history = self.get_conversation_history(session_id)
            if history:
                context['historico'] = history
                context['ultima_mensagem'] = history[-1] if history else None
            
            # Contexto armazenado
            stored_context = self.retrieve_conversation_context(session_id)
            if stored_context:
                context['contexto_anterior'] = stored_context
            
            # Preferências do usuário (se disponível no sistema)
            # TODO: Implementar quando houver sistema de preferências
            context['preferencias'] = {}
            
            return context
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter contexto: {e}")
            return {'session_id': session_id, 'error': str(e)}
    
    def save_interaction(self, session_id: str, query: str, response: str) -> bool:
        """
        Salva interação completa na memória.
        
        Args:
            session_id: ID da sessão
            query: Pergunta do usuário
            response: Resposta do sistema
            
        Returns:
            True se salvo com sucesso
        """
        try:
            # Criar mensagem estruturada
            interaction = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'response': response,
                'type': 'interaction'
            }
            
            # Adicionar à conversa
            success = self.add_conversation_message(session_id, interaction)
            
            # Atualizar contexto
            if success:
                context = {
                    'last_query': query,
                    'last_response': response,
                    'last_interaction': datetime.now().isoformat()
                }
                self.store_conversation_context(session_id, context)
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar interação: {e}")
            return False

    def set_processor(self, processor_manager):
        """Configura o ProcessorManager para processamento integrado"""
        try:
            self.processor_manager = processor_manager
            
            # Propagar para componentes que precisam
            if hasattr(self, 'context_memory') and self.context_memory:
                if hasattr(self.context_memory, 'set_processor'):
                    self.context_memory.set_processor(processor_manager)
                    
            if hasattr(self, 'conversation_memory') and self.conversation_memory:
                if hasattr(self.conversation_memory, 'set_processor'):
                    self.conversation_memory.set_processor(processor_manager)
                    
            logger.info("✅ ProcessorManager configurado no MemoryManager")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar processor: {e}")


# Instância global
_memory_manager = None

def get_memory_manager():
    """Retorna instância do MemoryManager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager 