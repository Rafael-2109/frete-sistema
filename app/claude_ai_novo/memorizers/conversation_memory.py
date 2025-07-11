#!/usr/bin/env python3
"""
🧠 CONVERSATION MEMORY - Memória de Conversa
============================================

Módulo responsável por memorizar conversas específicas.
Responsabilidade: MEMORIZAR conversas detalhadas.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from .context_memory import ContextMemory, get_context_memory

# Configurar logger
logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Memória especializada para conversas.
    
    Extends ContextMemory com funcionalidades específicas para conversas.
    """
    
    def __init__(self):
        """Inicializa a memória de conversa"""
        self.logger = logging.getLogger(__name__)
        self.context_memory = get_context_memory()
        self.conversation_timeout = 7200  # 2 horas
        
    def start_conversation(self, session_id: str, initial_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Inicia uma nova conversa.
        
        Args:
            session_id: ID da sessão
            initial_context: Contexto inicial (opcional)
            
        Returns:
            True se iniciado com sucesso
        """
        try:
            conversation_data = {
                'session_id': session_id,
                'started_at': datetime.now().isoformat(),
                'messages': [],
                'context': initial_context or {},
                'status': 'active'
            }
            
            return self.context_memory.store_context(session_id, conversation_data)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao iniciar conversa: {e}")
            return False
    
    def end_conversation(self, session_id: str) -> bool:
        """
        Finaliza uma conversa.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se finalizado com sucesso
        """
        try:
            context = self.context_memory.retrieve_context(session_id)
            if context:
                context['status'] = 'ended'
                context['ended_at'] = datetime.now().isoformat()
                return self.context_memory.store_context(session_id, context)
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao finalizar conversa: {e}")
            return False
    
    def add_user_message(self, session_id: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Adiciona mensagem do usuário.
        
        Args:
            session_id: ID da sessão
            message: Mensagem do usuário
            metadata: Metadados adicionais
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            message_data = {
                'type': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            return self.context_memory.add_message(session_id, message_data)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao adicionar mensagem do usuário: {e}")
            return False
    
    def add_assistant_message(self, session_id: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Adiciona mensagem do assistente.
        
        Args:
            session_id: ID da sessão
            message: Mensagem do assistente
            metadata: Metadados adicionais
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            message_data = {
                'type': 'assistant',
                'content': message,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            return self.context_memory.add_message(session_id, message_data)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao adicionar mensagem do assistente: {e}")
            return False
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna resumo da conversa.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dict com resumo da conversa
        """
        try:
            context = self.context_memory.retrieve_context(session_id)
            if not context:
                return {'error': 'Conversa não encontrada'}
            
            messages = context.get('messages', [])
            user_messages = [m for m in messages if m.get('type') == 'user']
            assistant_messages = [m for m in messages if m.get('type') == 'assistant']
            
            return {
                'session_id': session_id,
                'started_at': context.get('started_at'),
                'ended_at': context.get('ended_at'),
                'status': context.get('status', 'unknown'),
                'total_messages': len(messages),
                'user_messages': len(user_messages),
                'assistant_messages': len(assistant_messages),
                'duration': self._calculate_duration(context),
                'last_activity': messages[-1].get('timestamp') if messages else None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter resumo da conversa: {e}")
            return {'error': str(e)}
    
    def _calculate_duration(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Calcula duração da conversa.
        
        Args:
            context: Contexto da conversa
            
        Returns:
            String com duração ou None
        """
        try:
            started_at = context.get('started_at')
            ended_at = context.get('ended_at')
            
            if not started_at:
                return None
            
            start_time = datetime.fromisoformat(started_at)
            end_time = datetime.fromisoformat(ended_at) if ended_at else datetime.now()
            
            duration = end_time - start_time
            
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular duração: {e}")
            return None


# Instância global
_conversation_memory = None

def get_conversation_memory():
    """Retorna instância do ConversationMemory"""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory 