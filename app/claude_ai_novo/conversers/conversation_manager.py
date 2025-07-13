#!/usr/bin/env python3
"""
💬 CONVERSATION MANAGER - Gerenciador de Conversa
================================================

Módulo responsável por gerenciar conversas e diálogos.
Responsabilidade: GERENCIAR conversas completas.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

# Imports dos memorizadores
try:
    from app.claude_ai_novo.memorizers.context_memory import get_context_memory
    from app.claude_ai_novo.memorizers.conversation_memory import get_conversation_memory
except ImportError:
    from unittest.mock import Mock
    get_context_memory = Mock()
    get_conversation_memory = Mock()

# Configurar logger
logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Gerenciador de conversas completas.
    
    Coordena todo o fluxo de uma conversa, desde o início até o fim,
    integrando contexto, memória e processamento de mensagens.
    """
    
    def __init__(self):
        """Inicializa o gerenciador de conversa"""
        self.logger = logging.getLogger(__name__)
        self.context_memory = get_context_memory()
        self.conversation_memory = get_conversation_memory()
        self.active_conversations = {}
        
        # Configurações
        self.max_conversation_duration = 7200  # 2 horas
        self.max_messages_per_conversation = 100
        
        self.logger.info("💬 ConversationManager inicializado")
    
    def set_memorizer(self, memorizer):
        """
        Configura memorizer para gestão de memória.
        Implementa conexão Converser → Memorizer.
        
        Args:
            memorizer: Instância do MemoryManager
        """
        try:
            if hasattr(memorizer, 'context_memory'):
                self.context_memory = memorizer.context_memory
                self.logger.info("✅ Context Memory conectado via Memorizer")
            
            if hasattr(memorizer, 'conversation_memory'):
                self.conversation_memory = memorizer.conversation_memory
                self.logger.info("✅ Conversation Memory conectado via Memorizer")
            
            # Fallback se memorizer não tem as propriedades esperadas
            if not hasattr(memorizer, 'context_memory') and not hasattr(memorizer, 'conversation_memory'):
                self.logger.warning("⚠️ Memorizer não tem context_memory ou conversation_memory, mantendo configuração padrão")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao configurar memorizer: {e}")
            return False
    
    def start_conversation(self, user_id: str, initial_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Inicia uma nova conversa.
        
        Args:
            user_id: ID do usuário
            initial_message: Mensagem inicial (opcional)
            metadata: Metadados da conversa
            
        Returns:
            ID da sessão criada
        """
        try:
            # Gerar ID único da sessão
            session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Configurar contexto inicial
            initial_context = {
                'user_id': user_id,
                'started_at': datetime.now().isoformat(),
                'status': 'active',
                'metadata': metadata or {},
                'message_count': 0
            }
            
            # Iniciar conversa na memória
            if self.conversation_memory:
                self.conversation_memory.start_conversation(session_id, initial_context)
            
            # Armazenar contexto
            if self.context_memory:
                self.context_memory.store_context(session_id, initial_context)
            
            # Registrar conversa ativa
            self.active_conversations[session_id] = {
                'user_id': user_id,
                'started_at': datetime.now(),
                'last_activity': datetime.now(),
                'message_count': 0
            }
            
            # Adicionar mensagem inicial se fornecida
            if initial_message:
                self.add_user_message(session_id, initial_message)
            
            self.logger.info(f"💬 Nova conversa iniciada: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao iniciar conversa: {e}")
            return ""
    
    def add_user_message(self, session_id: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Adiciona mensagem do usuário à conversa.
        
        Args:
            session_id: ID da sessão
            message: Mensagem do usuário
            metadata: Metadados da mensagem
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            # Verificar se conversa está ativa
            if not self._is_conversation_active(session_id):
                self.logger.warning(f"⚠️ Tentativa de adicionar mensagem a conversa inativa: {session_id}")
                return False
            
            # Preparar dados da mensagem
            message_data = {
                'type': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Adicionar à memória de contexto
            success = False
            if self.context_memory:
                success = self.context_memory.add_message(session_id, message_data)
            
            # Adicionar à memória de conversa
            if self.conversation_memory:
                self.conversation_memory.add_user_message(session_id, message, metadata)
            
            # Atualizar conversa ativa
            if session_id in self.active_conversations:
                self.active_conversations[session_id]['last_activity'] = datetime.now()
                self.active_conversations[session_id]['message_count'] += 1
            
            self.logger.info(f"💬 Mensagem do usuário adicionada: {session_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao adicionar mensagem do usuário: {e}")
            return False
    
    def add_assistant_message(self, session_id: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Adiciona mensagem do assistente à conversa.
        
        Args:
            session_id: ID da sessão
            message: Mensagem do assistente
            metadata: Metadados da mensagem
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            # Verificar se conversa está ativa
            if not self._is_conversation_active(session_id):
                self.logger.warning(f"⚠️ Tentativa de adicionar resposta a conversa inativa: {session_id}")
                return False
            
            # Preparar dados da mensagem
            message_data = {
                'type': 'assistant',
                'content': message,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Adicionar à memória de contexto
            success = False
            if self.context_memory:
                success = self.context_memory.add_message(session_id, message_data)
            
            # Adicionar à memória de conversa
            if self.conversation_memory:
                self.conversation_memory.add_assistant_message(session_id, message, metadata)
            
            # Atualizar conversa ativa
            if session_id in self.active_conversations:
                self.active_conversations[session_id]['last_activity'] = datetime.now()
                self.active_conversations[session_id]['message_count'] += 1
            
            self.logger.info(f"💬 Mensagem do assistente adicionada: {session_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao adicionar mensagem do assistente: {e}")
            return False
    
    def get_conversation_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém contexto completo da conversa.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Contexto da conversa ou None
        """
        try:
            if self.context_memory:
                return self.context_memory.retrieve_context(session_id)
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter contexto da conversa: {e}")
            return None
    
    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtém histórico da conversa.
        
        Args:
            session_id: ID da sessão
            limit: Limite de mensagens
            
        Returns:
            Lista de mensagens
        """
        try:
            if self.context_memory:
                return self.context_memory.get_conversation_history(session_id, limit)
            return []
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter histórico da conversa: {e}")
            return []
    
    def end_conversation(self, session_id: str, reason: str = "user_ended") -> bool:
        """
        Finaliza uma conversa.
        
        Args:
            session_id: ID da sessão
            reason: Motivo do encerramento
            
        Returns:
            True se finalizado com sucesso
        """
        try:
            # Finalizar na memória de conversa
            if self.conversation_memory:
                self.conversation_memory.end_conversation(session_id)
            
            # Atualizar contexto com status final
            if self.context_memory:
                context = self.context_memory.retrieve_context(session_id)
                if context:
                    context['status'] = 'ended'
                    context['ended_at'] = datetime.now().isoformat()
                    context['end_reason'] = reason
                    self.context_memory.store_context(session_id, context)
            
            # Remover das conversas ativas
            if session_id in self.active_conversations:
                del self.active_conversations[session_id]
            
            self.logger.info(f"💬 Conversa finalizada: {session_id} (motivo: {reason})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao finalizar conversa: {e}")
            return False
    
    def get_active_conversations(self) -> List[Dict[str, Any]]:
        """
        Retorna lista de conversas ativas.
        
        Returns:
            Lista de conversas ativas
        """
        try:
            active_list = []
            
            for session_id, info in self.active_conversations.items():
                # Verificar se não expirou
                if self._is_conversation_active(session_id):
                    active_list.append({
                        'session_id': session_id,
                        'user_id': info['user_id'],
                        'started_at': info['started_at'].isoformat(),
                        'last_activity': info['last_activity'].isoformat(),
                        'message_count': info['message_count'],
                        'duration_minutes': int((datetime.now() - info['started_at']).total_seconds() / 60)
                    })
            
            return active_list
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter conversas ativas: {e}")
            return []
    
    def cleanup_expired_conversations(self) -> int:
        """
        Limpa conversas expiradas.
        
        Returns:
            Número de conversas limpas
        """
        try:
            cleaned = 0
            current_time = datetime.now()
            expired_sessions = []
            
            # Identificar conversas expiradas
            for session_id, info in self.active_conversations.items():
                time_since_activity = current_time - info['last_activity']
                if time_since_activity.total_seconds() > self.max_conversation_duration:
                    expired_sessions.append(session_id)
            
            # Finalizar conversas expiradas
            for session_id in expired_sessions:
                self.end_conversation(session_id, "expired")
                cleaned += 1
            
            # Limpar memórias expiradas
            if self.context_memory:
                cleaned += self.context_memory.cleanup_expired_contexts()
            
            if cleaned > 0:
                self.logger.info(f"🧹 Conversas expiradas limpas: {cleaned}")
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar conversas expiradas: {e}")
            return 0
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Retorna resumo da conversa.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dict com resumo da conversa
        """
        try:
            if self.conversation_memory:
                return self.conversation_memory.get_conversation_summary(session_id)
            
            # Fallback básico
            context = self.get_conversation_context(session_id)
            if context:
                return {
                    'session_id': session_id,
                    'status': context.get('status', 'unknown'),
                    'started_at': context.get('started_at'),
                    'message_count': context.get('message_count', 0),
                    'source': 'context_fallback'
                }
            
            return {'error': 'Conversa não encontrada'}
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter resumo da conversa: {e}")
            return {'error': str(e)}
    
    def _is_conversation_active(self, session_id: str) -> bool:
        """
        Verifica se conversa está ativa.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se ativa, False caso contrário
        """
        try:
            if session_id not in self.active_conversations:
                return False
            
            info = self.active_conversations[session_id]
            time_since_activity = datetime.now() - info['last_activity']
            
            # Verificar timeout
            if time_since_activity.total_seconds() > self.max_conversation_duration:
                return False
            
            # Verificar limite de mensagens
            if info['message_count'] > self.max_messages_per_conversation:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar se conversa está ativa: {e}")
            return False
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do gerenciador.
        
        Returns:
            Dict com estatísticas
        """
        try:
            return {
                'active_conversations': len(self.active_conversations),
                'max_conversation_duration': self.max_conversation_duration,
                'max_messages_per_conversation': self.max_messages_per_conversation,
                'context_memory_available': self.context_memory is not None,
                'conversation_memory_available': self.conversation_memory is not None,
                'module': 'ConversationManager',
                'version': '1.0.0'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {'error': str(e)}


# Instância global
_conversation_manager = None

def get_conversation_manager():
    """Retorna instância do ConversationManager"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager 