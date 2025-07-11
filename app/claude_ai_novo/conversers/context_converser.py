#!/usr/bin/env python3
"""
Sistema de Contexto Conversacional - Sistema de Fretes
Implementa memória conversacional para Claude AI com persistência Redis
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ConversationMessage:
    """Mensagem individual na conversa"""
    role: str  # 'user' ou 'assistant'
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return asdict(self)

class ConversationContext:
    """
    Gerenciador de contexto conversacional com persistência Redis
    Baseado em: https://medium.com/@rendysatriadalimunthe/showcasing-a-context-aware-conversational-ai-85cf13af2891
    """
    
    def __init__(self, redis_cache=None):
        self.redis_cache = redis_cache
        self.context_ttl = 3600  # 1 hora de TTL para contexto
        self.max_messages = 20   # Máximo de mensagens no contexto
        
        # Configurações de contexto
        self.system_prompt = """Você é um assistente especializado em logística e fretes. 
        Use o HISTÓRICO da conversa anterior para dar respostas contextuais e coerentes.
        Se o usuário fizer perguntas de seguimento como "E em maio?" ou "E esse cliente?", 
        use o contexto anterior para entender sobre qual cliente/período ele está perguntando.
        
        IMPORTANTE: Sempre mantenha a continuidade da conversa."""
    
    def _get_context_key(self, user_id: str) -> str:
        """Gera chave única para contexto do usuário no Redis"""
        return f"conversation_context:{user_id}"
    
    def add_message(self, user_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Adiciona nova mensagem ao contexto da conversa
        
        Args:
            user_id: ID único do usuário
            role: 'user' ou 'assistant'
            content: Conteúdo da mensagem
            metadata: Dados adicionais (cliente detectado, período, etc.)
        """
        try:
            message = ConversationMessage(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                metadata=metadata or {}
            )
            
            # Buscar contexto existente
            context_history = self.get_context(user_id)
            
            # Adicionar nova mensagem
            context_history.append(message.to_dict())
            
            # Manter apenas as últimas N mensagens
            if len(context_history) > self.max_messages:
                context_history = context_history[-self.max_messages:]
            
            # Salvar no Redis se disponível
            if self.redis_cache and self.redis_cache.disponivel:
                context_key = self._get_context_key(user_id)
                success = self.redis_cache.set(context_key, context_history, self.context_ttl)
                if success:
                    logger.debug(f"✅ Contexto salvo no Redis para usuário {user_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Falha ao salvar contexto no Redis para usuário {user_id}")
            
            # Fallback: usar cache em memória (temporário)
            if not hasattr(self, '_memory_cache'):
                self._memory_cache = {}
            
            self._memory_cache[user_id] = {
                'history': context_history,
                'expires': datetime.now() + timedelta(seconds=self.context_ttl)
            }
            
            logger.debug(f"💾 Contexto salvo em memória para usuário {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar mensagem ao contexto: {e}")
            return False
    
    def get_context(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Recupera histórico de contexto do usuário
        
        Returns:
            Lista de mensagens da conversa
        """
        try:
            # Tentar Redis primeiro
            if self.redis_cache and self.redis_cache.disponivel:
                context_key = self._get_context_key(user_id)
                context_data = self.redis_cache.get(context_key)
                
                if context_data:
                    logger.debug(f"🎯 Contexto recuperado do Redis para usuário {user_id}")
                    return context_data
            
            # Fallback: cache em memória
            if hasattr(self, '_memory_cache') and user_id in self._memory_cache:
                cache_entry = self._memory_cache[user_id]
                
                # Verificar expiração
                if datetime.now() < cache_entry['expires']:
                    logger.debug(f"💾 Contexto recuperado da memória para usuário {user_id}")
                    return cache_entry['history']
                else:
                    # Contexto expirado
                    del self._memory_cache[user_id]
                    logger.debug(f"⏰ Contexto expirado removido para usuário {user_id}")
            
            # Sem contexto encontrado
            logger.debug(f"🆕 Nenhum contexto encontrado para usuário {user_id}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar contexto: {e}")
            return []
    
    def build_context_prompt(self, user_id: str, new_question: str) -> str:
        """
        Constrói prompt completo com contexto histórico
        
        Args:
            user_id: ID do usuário
            new_question: Nova pergunta do usuário
            
        Returns:
            Prompt completo com contexto
        """
        try:
            # Recuperar histórico
            history = self.get_context(user_id)
            
            if not history:
                # Sem histórico - pergunta independente
                return new_question
            
            # Construir contexto histórico
            context_lines = ["=== HISTÓRICO DA CONVERSA ==="]
            
            for msg in history[-10:]:  # Últimas 10 mensagens
                role_emoji = "👤" if msg['role'] == 'user' else "🤖"
                timestamp = msg.get('timestamp', '')
                content = msg.get('content', '')
                
                # Adicionar metadados se existirem
                metadata = msg.get('metadata', {})
                metadata_info = ""
                if metadata:
                    if 'cliente_detectado' in metadata:
                        metadata_info = f" [Cliente: {metadata['cliente_detectado']}]"
                    if 'periodo_detectado' in metadata:
                        metadata_info += f" [Período: {metadata['periodo_detectado']}]"
                
                context_lines.append(f"{role_emoji} {content}{metadata_info}")
            
            context_lines.append("=== NOVA PERGUNTA ===")
            context_lines.append(f"👤 {new_question}")
            context_lines.append("")
            context_lines.append("🧠 INSTRUÇÕES: Use o histórico acima para entender o contexto.")
            context_lines.append("Se a nova pergunta se refere a algo mencionado anteriormente (cliente, período, etc.), mantenha a continuidade.")
            
            full_prompt = "\n".join(context_lines)
            
            logger.debug(f"🧠 Prompt contextual construído para usuário {user_id} ({len(history)} mensagens)")
            return full_prompt
            
        except Exception as e:
            logger.error(f"❌ Erro ao construir prompt contextual: {e}")
            return new_question
    
    def extract_metadata(self, user_question: str, ai_response: str) -> Dict[str, Any]:
        """
        Extrai metadados da conversa para melhor contexto
        
        Args:
            user_question: Pergunta do usuário
            ai_response: Resposta da IA
            
        Returns:
            Dicionário com metadados extraídos
        """
        metadata = {}
        
        try:
            # Detectar clientes mencionados
            clientes_conhecidos = ['Assai', 'Atacadão', 'Carrefour', 'Tenda', 'Mateus', 'Fort']
            for cliente in clientes_conhecidos:
                if cliente.lower() in user_question.lower() or cliente.lower() in ai_response.lower():
                    metadata['cliente_detectado'] = cliente
                    break
            
            # Detectar períodos/meses
            meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            for mes in meses:
                if mes in user_question.lower() or mes in ai_response.lower():
                    metadata['periodo_detectado'] = mes.capitalize()
                    break
            
            # Detectar tipos de consulta
            if any(word in user_question.lower() for word in ['quantas', 'quantidade', 'total']):
                metadata['tipo_consulta'] = 'quantitativa'
            elif any(word in user_question.lower() for word in ['listar', 'mostrar', 'quais']):
                metadata['tipo_consulta'] = 'listagem'
            
            logger.debug(f"🔍 Metadados extraídos: {metadata}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair metadados: {e}")
        
        return metadata
    
    def clear_context(self, user_id: str) -> bool:
        """
        Limpa contexto de um usuário específico
        
        Args:
            user_id: ID do usuário
            
        Returns:
            True se limpeza foi bem-sucedida
        """
        try:
            # Limpar do Redis
            if self.redis_cache and self.redis_cache.disponivel:
                context_key = self._get_context_key(user_id)
                self.redis_cache.delete(context_key)
                logger.info(f"🗑️ Contexto Redis limpo para usuário {user_id}")
            
            # Limpar da memória
            if hasattr(self, '_memory_cache') and user_id in self._memory_cache:
                del self._memory_cache[user_id]
                logger.info(f"🗑️ Contexto memória limpo para usuário {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar contexto: {e}")
            return False
    
    def get_context_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Retorna resumo do contexto atual do usuário
        
        Returns:
            Dicionário com informações do contexto
        """
        try:
            history = self.get_context(user_id)
            
            if not history:
                return {
                    'has_context': False,
                    'message_count': 0,
                    'last_interaction': None
                }
            
            # Extrair informações do contexto
            last_message = history[-1] if history else None
            user_messages = [msg for msg in history if msg['role'] == 'user']
            assistant_messages = [msg for msg in history if msg['role'] == 'assistant']
            
            # Detectar temas principais
            all_content = " ".join([msg['content'] for msg in history])
            clientes_mencionados = []
            clientes_conhecidos = ['Assai', 'Atacadão', 'Carrefour', 'Tenda', 'Mateus', 'Fort']
            
            for cliente in clientes_conhecidos:
                if cliente.lower() in all_content.lower():
                    clientes_mencionados.append(cliente)
            
            return {
                'has_context': True,
                'message_count': len(history),
                'user_messages': len(user_messages),
                'assistant_messages': len(assistant_messages),
                'last_interaction': last_message['timestamp'] if last_message else None,
                'clientes_mencionados': clientes_mencionados,
                'storage_type': 'redis' if (self.redis_cache and self.redis_cache.disponivel) else 'memory'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar resumo do contexto: {e}")
            return {'has_context': False, 'error': str(e)}


# Instância global do gerenciador de contexto
conversation_context = None

def init_conversation_context(redis_cache=None):
    """Inicializa o gerenciador de contexto conversacional"""
    global conversation_context
    try:
        conversation_context = ConversationContext(redis_cache)
        logger.info("🧠 Sistema de Contexto Conversacional inicializado")
        return conversation_context
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar contexto conversacional: {e}")
        return None

def get_conversation_context():
    """Retorna instância do gerenciador de contexto"""
    return conversation_context 