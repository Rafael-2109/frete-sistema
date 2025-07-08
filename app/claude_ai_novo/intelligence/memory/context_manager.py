"""
🧠 CONTEXT MANAGER
Gerenciamento de contexto conversacional
"""

from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ContextManager:
    """Gerenciador de contexto conversacional"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.memory_fallback = {}
        self.max_messages = 20
        self.ttl_hours = 1
        
    def enrich_query(self, query: str, user_context: Dict[str, Any]) -> str:
        """Enriquece consulta com contexto conversacional"""
        
        user_id = user_context.get('user_id', 'anonymous')
        conversation_history = self.get_conversation_history(user_id)
        
        if not conversation_history:
            return query
            
        # Construir contexto a partir do histórico
        context_prompt = self._build_context_prompt(conversation_history)
        
        if context_prompt:
            return f"{context_prompt}\n\nNova pergunta: {query}"
        
        return query
    
    def add_message(self, user_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Adiciona mensagem ao contexto"""
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        try:
            if self.redis_client:
                self._add_to_redis(user_id, message)
            else:
                self._add_to_memory(user_id, message)
        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem: {e}")
    
    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Obtém histórico da conversa"""
        
        try:
            if self.redis_client:
                return self._get_from_redis(user_id)
            else:
                return self._get_from_memory(user_id)
        except Exception as e:
            logger.error(f"Erro ao obter histórico: {e}")
            return []
    
    def clear_context(self, user_id: str):
        """Limpa contexto do usuário"""
        
        try:
            if self.redis_client:
                self.redis_client.delete(f"conversation:{user_id}")
            else:
                self.memory_fallback.pop(user_id, None)
        except Exception as e:
            logger.error(f"Erro ao limpar contexto: {e}")
    
    def _build_context_prompt(self, history: List[Dict]) -> str:
        """Constrói prompt de contexto"""
        
        if len(history) < 2:
            return ""
            
        recent_messages = history[-6:]  # Últimas 6 mensagens
        context_parts = []
        
        for msg in recent_messages:
            role = "Usuário" if msg['role'] == 'user' else "Assistente"
            content = msg['content'][:200]  # Limitar tamanho
            context_parts.append(f"{role}: {content}")
        
        return f"Contexto da conversa anterior:\n" + "\n".join(context_parts)
    
    def _add_to_redis(self, user_id: str, message: Dict):
        """Adiciona mensagem ao Redis"""
        key = f"conversation:{user_id}"
        self.redis_client.lpush(key, json.dumps(message))
        self.redis_client.ltrim(key, 0, self.max_messages - 1)
        self.redis_client.expire(key, self.ttl_hours * 3600)
    
    def _get_from_redis(self, user_id: str) -> List[Dict]:
        """Obtém mensagens do Redis"""
        key = f"conversation:{user_id}"
        messages = self.redis_client.lrange(key, 0, -1)
        return [json.loads(msg) for msg in messages]
    
    def _add_to_memory(self, user_id: str, message: Dict):
        """Adiciona mensagem à memória"""
        if user_id not in self.memory_fallback:
            self.memory_fallback[user_id] = []
        
        self.memory_fallback[user_id].insert(0, message)
        
        # Limitar número de mensagens
        if len(self.memory_fallback[user_id]) > self.max_messages:
            self.memory_fallback[user_id] = self.memory_fallback[user_id][:self.max_messages]
    
    def _get_from_memory(self, user_id: str) -> List[Dict]:
        """Obtém mensagens da memória"""
        return self.memory_fallback.get(user_id, [])
