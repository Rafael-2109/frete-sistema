#!/usr/bin/env python3
"""
🧠 CONTEXT MEMORY - Memória de Contexto
=======================================

Módulo responsável por memorizar e gerenciar contexto de conversas.
Responsabilidade: MEMORIZAR contexto conversacional.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json

# Flask fallback para execução standalone
try:
    from app.utils.redis_cache import redis_cache, REDIS_DISPONIVEL
    from app.claude_ai_novo.utils.flask_fallback import get_current_user
except ImportError:
    redis_cache = None
    REDIS_DISPONIVEL = False
    get_current_user = lambda: None

try:
    from flask_login import current_user as flask_current_user
    FLASK_LOGIN_AVAILABLE = True
    current_user = flask_current_user
except ImportError:
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
            def __call__(self, *args, **kwargs):
                return self
            def __getattr__(self, name):
                return self
    
    flask_current_user = Mock()
    FLASK_LOGIN_AVAILABLE = False
    current_user = get_current_user() if get_current_user else flask_current_user

# Configurar logger
logger = logging.getLogger(__name__)

class ContextMemory:
    """
    Memória de contexto para conversas e interações.
    
    Responsável por armazenar e recuperar contexto de conversas,
    mantendo histórico de interações e estado conversacional.
    """
    
    def __init__(self):
        """Inicializa a memória de contexto"""
        self.logger = logging.getLogger(__name__)
        self.memory_timeout = 3600  # 1 hora
        self.max_messages = 50      # Máximo de mensagens por contexto
        self.local_cache = {}       # Cache local como fallback
        
    def store_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """
        Armazena contexto de uma sessão.
        
        Args:
            session_id: ID da sessão
            context: Contexto para armazenar
            
        Returns:
            True se armazenado com sucesso, False caso contrário
        """
        try:
            # Adicionar timestamp
            context['timestamp'] = datetime.now().isoformat()
            context['session_id'] = session_id
            
            # Limitar tamanho do contexto
            if len(str(context)) > 100000:  # 100KB máximo
                context = self._compress_context(context)
            
            # Tentar armazenar no Redis primeiro
            if REDIS_DISPONIVEL:
                key = f"context_memory:{session_id}"
                if redis_cache:
                    redis_cache.set(key, context, ttl=self.memory_timeout)
                    self.logger.info(f"✅ Contexto armazenado no Redis: {session_id}")
                    return True
            else:
                # Fallback para cache local
                self.local_cache[session_id] = {
                    'context': context,
                    'timestamp': datetime.now().timestamp()
                }
                self.logger.info(f"✅ Contexto armazenado localmente: {session_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao armazenar contexto: {e}")
            return False
    
    def retrieve_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera contexto de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Contexto da sessão ou None se não encontrado
        """
        try:
            # Tentar recuperar do Redis primeiro
            if REDIS_DISPONIVEL:
                key = f"context_memory:{session_id}"
                context = redis_cache.get(key) if redis_cache else None
                if context:
                    self.logger.info(f"✅ Contexto recuperado do Redis: {session_id}")
                    return context
            
            # Fallback para cache local
            if session_id in self.local_cache:
                cached = self.local_cache[session_id]
                # Verificar se não expirou
                if datetime.now().timestamp() - cached['timestamp'] < self.memory_timeout:
                    self.logger.info(f"✅ Contexto recuperado localmente: {session_id}")
                    return cached['context']
                else:
                    # Remover contexto expirado
                    del self.local_cache[session_id]
            
            self.logger.info(f"📭 Contexto não encontrado: {session_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar contexto: {e}")
            return None
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Adiciona mensagem ao contexto de uma sessão.
        
        Args:
            session_id: ID da sessão
            message: Mensagem para adicionar
            
        Returns:
            True se adicionado com sucesso, False caso contrário
        """
        try:
            # Recuperar contexto existente
            context = self.retrieve_context(session_id) or {'messages': []}
            
            # Adicionar timestamp à mensagem
            message['timestamp'] = datetime.now().isoformat()
            
            # Adicionar mensagem
            if 'messages' not in context:
                context['messages'] = []
            
            context['messages'].append(message)
            
            # Limitar número de mensagens
            if len(context['messages']) > self.max_messages:
                context['messages'] = context['messages'][-self.max_messages:]
            
            # Armazenar contexto atualizado
            return self.store_context(session_id, context)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao adicionar mensagem: {e}")
            return False
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recupera histórico de conversa de uma sessão.
        
        Args:
            session_id: ID da sessão
            limit: Limite de mensagens a retornar
            
        Returns:
            Lista de mensagens do histórico
        """
        try:
            context = self.retrieve_context(session_id)
            if not context or 'messages' not in context:
                return []
            
            messages = context['messages']
            
            # Retornar últimas mensagens
            return messages[-limit:] if len(messages) > limit else messages
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter histórico: {e}")
            return []
    
    def clear_context(self, session_id: str) -> bool:
        """
        Limpa contexto de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se limpo com sucesso, False caso contrário
        """
        try:
            # Limpar do Redis
            if REDIS_DISPONIVEL:
                key = f"context_memory:{session_id}"
                if REDIS_AVAILABLE and redis_cache:
                    redis_cache.delete(key)
            
            # Limpar do cache local
            if session_id in self.local_cache:
                del self.local_cache[session_id]
            
            self.logger.info(f"✅ Contexto limpo: {session_id}")
            return True
            
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
            active_sessions = []
            
            # Verificar cache local
            current_time = datetime.now().timestamp()
            for session_id, cached in self.local_cache.items():
                if current_time - cached['timestamp'] < self.memory_timeout:
                    active_sessions.append(session_id)
            
            return active_sessions
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter sessões ativas: {e}")
            return []
    
    def cleanup_expired_contexts(self) -> int:
        """
        Limpa contextos expirados.
        
        Returns:
            Número de contextos limpos
        """
        try:
            cleaned = 0
            current_time = datetime.now().timestamp()
            
            # Limpar cache local
            expired_sessions = []
            for session_id, cached in self.local_cache.items():
                if current_time - cached['timestamp'] >= self.memory_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.local_cache[session_id]
                cleaned += 1
            
            if cleaned > 0:
                self.logger.info(f"🧹 Contextos expirados limpos: {cleaned}")
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao limpar contextos expirados: {e}")
            return 0
    
    def _compress_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprime contexto removendo dados desnecessários.
        
        Args:
            context: Contexto para comprimir
            
        Returns:
            Contexto comprimido
        """
        try:
            compressed = context.copy()
            
            # Limitar mensagens
            if 'messages' in compressed and len(compressed['messages']) > self.max_messages:
                compressed['messages'] = compressed['messages'][-self.max_messages:]
            
            # Remover dados muito grandes
            for key, value in list(compressed.items()):
                if isinstance(value, str) and len(value) > 10000:
                    compressed[key] = value[:10000] + "... [truncado]"
                elif isinstance(value, list) and len(value) > 100:
                    compressed[key] = value[:100]
            
            return compressed
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao comprimir contexto: {e}")
            return context
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da memória.
        
        Returns:
            Dict com estatísticas
        """
        try:
            return {
                'active_sessions': len(self.get_active_sessions()),
                'local_cache_size': len(self.local_cache),
                'memory_timeout': self.memory_timeout,
                'max_messages': self.max_messages,
                'redis_available': REDIS_DISPONIVEL,
                'module': 'ContextMemory',
                'version': '1.0.0'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {'error': str(e)}


# Instância global
_context_memory = None

def get_context_memory():
    """Retorna instância do ContextMemory"""
    global _context_memory
    if _context_memory is None:
        _context_memory = ContextMemory()
    return _context_memory 