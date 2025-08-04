#!/usr/bin/env python3
"""
Sistema de Contexto Conversacional - Sistema de Fretes
Implementa memória conversacional para Claude AI com persistência Redis
"""

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

# ... [mantido todo o cabeçalho e imports anteriores] ...

class ConversationContext:
    def __init__(self, redis_cache=None):
        self.redis_cache = redis_cache
        self.context_ttl = 3600
        self.max_messages = 20

        self.system_prompt = """Você é um assistente especializado em logística e fretes. 
        Use o HISTÓRICO da conversa anterior para dar respostas contextuais e coerentes.
        IMPORTANTE: Sempre mantenha a continuidade da conversa."""

    def _get_context_key(self, user_id: str) -> str:
        return f"conversation_context:{user_id}"

    def add_message(self, user_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            message = ConversationMessage(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                metadata=metadata or {}
            )

            context_history = self.get_context(user_id)
            context_history.append(message.to_dict())

            if len(context_history) > self.max_messages:
                context_history = context_history[-self.max_messages:]

            context_key = self._get_context_key(user_id)

            if self.redis_cache:
                try:
                    self.redis_cache.set(context_key, str(context_history), ex=self.context_ttl)
                    logger.debug(f"✅ Contexto salvo no Redis para usuário {user_id}")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Falha ao salvar no Redis: {e}")

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
        try:
            context_key = self._get_context_key(user_id)

            if self.redis_cache:
                try:
                    context_data = self.redis_cache.get(context_key)
                    if context_data:
                        logger.debug(f"🎯 Contexto recuperado do Redis para usuário {user_id}")
                        return eval(context_data)
                except Exception as e:
                    logger.warning(f"⚠️ Falha ao recuperar do Redis: {e}")

            if hasattr(self, '_memory_cache') and user_id in self._memory_cache:
                cache_entry = self._memory_cache[user_id]
                if datetime.now() < cache_entry['expires']:
                    logger.debug(f"💾 Contexto recuperado da memória para usuário {user_id}")
                    return cache_entry['history']
                else:
                    del self._memory_cache[user_id]

            return []

        except Exception as e:
            logger.error(f"❌ Erro ao recuperar contexto: {e}")
            return []

    def clear_context(self, user_id: str) -> bool:
        try:
            context_key = self._get_context_key(user_id)

            if self.redis_cache:
                try:
                    self.redis_cache.delete(context_key)
                    logger.info(f"🗑️ Contexto Redis limpo para usuário {user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Falha ao limpar Redis: {e}")

            if hasattr(self, '_memory_cache') and user_id in self._memory_cache:
                del self._memory_cache[user_id]
                logger.info(f"🗑️ Contexto memória limpo para usuário {user_id}")

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao limpar contexto: {e}")
            return False

    def build_context_prompt(self, user_id: str, new_question: str) -> str:
        try:
            history = self.get_context(user_id)

            if not history:
                return new_question

            context_lines = ["=== HISTÓRICO DA CONVERSA ==="]

            for msg in history[-10:]:
                role_emoji = "👤" if msg['role'] == 'user' else "🤖"
                content = msg.get('content', '')
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
            context_lines.append("🧠 INSTRUÇÕES: Use o histórico acima para entender o contexto.")

            return "\n".join(context_lines)

        except Exception as e:
            logger.error(f"❌ Erro ao construir prompt contextual: {e}")
            return new_question

    def extract_metadata(self, user_question: str, ai_response: str) -> Dict[str, Any]:
        metadata = {}
        try:
            clientes_conhecidos = ['Assai', 'Atacadão', 'Carrefour', 'Tenda', 'Mateus', 'Fort']
            for cliente in clientes_conhecidos:
                if cliente.lower() in user_question.lower() or cliente.lower() in ai_response.lower():
                    metadata['cliente_detectado'] = cliente
                    break

            meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                     'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            for mes in meses:
                if mes in user_question.lower() or mes in ai_response.lower():
                    metadata['periodo_detectado'] = mes.capitalize()
                    break

            if any(w in user_question.lower() for w in ['quantas', 'quantidade', 'total']):
                metadata['tipo_consulta'] = 'quantitativa'
            elif any(w in user_question.lower() for w in ['listar', 'mostrar', 'quais']):
                metadata['tipo_consulta'] = 'listagem'

        except Exception as e:
            logger.error(f"❌ Erro ao extrair metadados: {e}")
        return metadata

    def get_context_summary(self, user_id: str) -> Dict[str, Any]:
        try:
            history = self.get_context(user_id)
            if not history:
                return {'has_context': False, 'message_count': 0, 'last_interaction': None}

            last_message = history[-1]
            user_messages = [msg for msg in history if msg['role'] == 'user']
            assistant_messages = [msg for msg in history if msg['role'] == 'assistant']

            clientes_conhecidos = ['Assai', 'Atacadão', 'Carrefour', 'Tenda', 'Mateus', 'Fort']
            all_content = " ".join([msg['content'] for msg in history])
            clientes_mencionados = [c for c in clientes_conhecidos if c.lower() in all_content.lower()]

            return {
                'has_context': True,
                'message_count': len(history),
                'user_messages': len(user_messages),
                'assistant_messages': len(assistant_messages),
                'last_interaction': last_message['timestamp'],
                'clientes_mencionados': clientes_mencionados,
                'storage_type': 'redis' if self.redis_cache else 'memory'
            }

        except Exception as e:
            logger.error(f"❌ Erro ao gerar resumo do contexto: {e}")
            return {'has_context': False, 'error': str(e)}

# Instância global
conversation_context = None

def init_conversation_context(redis_cache=None):
    global conversation_context
    try:
        conversation_context = ConversationContext(redis_cache)
        logger.info("🧠 Sistema de Contexto Conversacional inicializado")
        return conversation_context
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar contexto: {e}")
        return None

def get_conversation_context():
    return conversation_context
