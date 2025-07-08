#!/usr/bin/env python3
"""
Sistema de Sugestões Inteligentes - Claude AI
Gera sugestões contextuais baseadas no perfil do usuário e histórico conversacional
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import random

logger = logging.getLogger(__name__)

@dataclass
class Suggestion:
    """Estrutura de uma sugestão inteligente"""
    text: str
    category: str
    priority: int  # 1-5 (5 = mais importante)
    icon: str
    description: str
    user_profiles: List[str]  # Perfis que podem ver esta sugestão
    context_keywords: Optional[List[str]] = None  # Palavras-chave que ativam esta sugestão
    
    def to_dict(self):
        return {
            'text': self.text,
            'category': self.category,
            'priority': self.priority,
            'icon': self.icon,
            'description': self.description,
            'user_profiles': self.user_profiles,
            'context_keywords': self.context_keywords or []
        }

class SuggestionEngine:
    """
    Engine de Sugestões Inteligentes
    Baseado em: https://www.visiativ.com/en/actualites/news/7-tips-for-implementing-a-smart-chatbot/
    """
    
    def __init__(self, redis_cache=None):
        self.redis_cache = redis_cache
        self.cache_ttl = 300  # 5 minutos para sugestões
        
        # Base de sugestões pré-definidas por categoria
        self.base_suggestions = self._initialize_base_suggestions()
        
        logger.info("🧠 Sistema de Sugestões Inteligentes inicializado")
    
    def _initialize_base_suggestions(self) -> List[Suggestion]:
        """Inicializa base de sugestões categorizadas por perfil"""
        return [
            # 📊 SUGESTÕES PARA VENDEDORES
            Suggestion(
                text="Status dos meus clientes hoje",
                category="vendedor_diario",
                priority=5,
                icon="📋",
                description="Resumo diário das entregas dos seus clientes",
                user_profiles=["vendedor"],
                context_keywords=["cliente", "status", "hoje"]
            ),
            Suggestion(
                text="Entregas atrasadas da minha carteira",
                category="vendedor_problemas",
                priority=4,
                icon="⚠️",
                description="Entregas em atraso que precisam de atenção",
                user_profiles=["vendedor"],
                context_keywords=["atraso", "atrasadas", "problema"]
            ),
            Suggestion(
                text="Clientes sem pedidos nos últimos 15 dias",
                category="vendedor_oportunidade",
                priority=3,
                icon="🔍",
                description="Clientes inativos que podem precisar de contato",
                user_profiles=["vendedor"],
                context_keywords=["inativo", "sem pedidos", "oportunidade"]
            ),
            
            # 💰 SUGESTÕES PARA FINANCEIRO
            Suggestion(
                text="Faturas em aberto por vencer",
                category="financeiro_urgente",
                priority=5,
                icon="💸",
                description="Faturas próximas do vencimento",
                user_profiles=["financeiro", "admin"],
                context_keywords=["fatura", "vencimento", "aberto"]
            ),
            Suggestion(
                text="Performance de pagamentos do mês",
                category="financeiro_analise",
                priority=4,
                icon="📊",
                description="Análise financeira mensal de recebimentos",
                user_profiles=["financeiro", "admin"],
                context_keywords=["pagamento", "recebimento", "mensal"]
            ),
            
            # 🚛 SUGESTÕES PARA OPERACIONAL
            Suggestion(
                text="Embarques aguardando liberação",
                category="operacional_urgente",
                priority=5,
                icon="🚨",
                description="Embarques pendentes de liberação",
                user_profiles=["operacional", "admin"],
                context_keywords=["embarque", "liberação", "pendente"]
            ),
            Suggestion(
                text="Entregas para hoje",
                category="operacional_diario",
                priority=4,
                icon="📦",
                description="Programação de entregas do dia",
                user_profiles=["operacional", "admin", "vendedor"],
                context_keywords=["entrega", "hoje", "programação"]
            ),
            
            # 📈 SUGESTÕES GERAIS
            Suggestion(
                text="Resumo executivo do sistema",
                category="admin_dashboard",
                priority=4,
                icon="🎯",
                description="Visão geral do status do sistema",
                user_profiles=["admin"],
                context_keywords=["resumo", "dashboard", "geral"]
            ),
            
            # 🔥 SUGESTÕES CONTEXTUAIS
            Suggestion(
                text="Compare com o mês anterior",
                category="contextual_comparacao",
                priority=4,
                icon="⚖️",
                description="Comparação temporal dos dados consultados",
                user_profiles=["vendedor", "financeiro", "operacional", "admin"],
                context_keywords=["dados", "resultado", "entrega", "fatura"]
            )
        ]
    
    def generate_suggestions(self, user_context: Dict[str, Any], conversation_context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Método principal para gerar sugestões (nome alternativo)
        
        Args:
            user_context: Informações do usuário (perfil, vendedor_codigo, etc.)
            conversation_context: Contexto da conversa atual
            
        Returns:
            Lista de sugestões personalizadas
        """
        return self.get_intelligent_suggestions(user_context, conversation_context)
    
    def get_intelligent_suggestions(self, user_context: Dict[str, Any], conversation_context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Gera sugestões inteligentes baseadas no contexto do usuário e conversa
        
        Args:
            user_context: Informações do usuário (perfil, vendedor_codigo, etc.)
            conversation_context: Contexto da conversa atual
            
        Returns:
            Lista de sugestões personalizadas
        """
        try:
            # 🔍 VALIDAR TIPOS DE ENTRADA
            if not isinstance(user_context, dict):
                logger.error(f"❌ user_context deve ser dict, recebido: {type(user_context)}")
                return self._get_fallback_suggestions({'perfil': 'usuario'})
            
            if conversation_context is not None and not isinstance(conversation_context, dict):
                logger.warning(f"⚠️ conversation_context deve ser dict, recebido: {type(conversation_context)}, ignorando")
                conversation_context = None
            
            # Cache key baseado no usuário e contexto
            cache_key = self._generate_cache_key(user_context, conversation_context)
            
            # Tentar buscar do cache Redis com validação robusta
            if self._is_redis_available():
                try:
                    cached_suggestions = self.redis_cache.get(cache_key)
                    if cached_suggestions and isinstance(cached_suggestions, list):
                        logger.debug(f"🎯 Sugestões carregadas do cache para usuário {user_context.get('username', 'unknown')}")
                        return cached_suggestions
                except Exception as redis_error:
                    logger.warning(f"⚠️ Erro no Redis cache: {redis_error}, continuando sem cache")
            
            # Gerar sugestões dinamicamente
            suggestions = self._generate_suggestions(user_context, conversation_context)
            
            # Salvar no cache com validação
            if self._is_redis_available() and isinstance(suggestions, list):
                try:
                    self.redis_cache.set(cache_key, suggestions, ttl=self.cache_ttl)
                    logger.debug(f"💾 Sugestões salvas no cache para usuário {user_context.get('username', 'unknown')}")
                except Exception as redis_error:
                    logger.warning(f"⚠️ Erro ao salvar no Redis: {redis_error}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sugestões inteligentes: {e}")
            # Garantir que user_context seja dict para fallback
            safe_context = user_context if isinstance(user_context, dict) else {'perfil': 'usuario'}
            return self._get_fallback_suggestions(safe_context)
    
    def _is_redis_available(self) -> bool:
        """Verifica se Redis está disponível e configurado corretamente"""
        try:
            return (
                self.redis_cache is not None and 
                hasattr(self.redis_cache, 'disponivel') and 
                hasattr(self.redis_cache, 'get') and 
                hasattr(self.redis_cache, 'set') and
                self.redis_cache.disponivel
            )
        except Exception:
            return False
    
    def _generate_suggestions(self, user_context: Dict[str, Any], conversation_context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Gera sugestões baseadas no contexto atual"""
        
        try:
            user_profile = user_context.get('perfil', 'usuario').lower()
            username = user_context.get('username', 'Usuario')
            vendedor_codigo = user_context.get('vendedor_codigo')
            
            # Filtrar sugestões por perfil
            profile_suggestions = [
                s for s in self.base_suggestions 
                if user_profile in s.user_profiles or 'admin' in s.user_profiles
            ]
            
            # 🧠 GERAR SUGESTÕES BASEADAS EM DADOS REAIS (VERSÃO SIMPLIFICADA)
            data_based_suggestions = self._generate_data_based_suggestions_simple(user_context)
            
            # Analisar contexto conversacional para sugestões contextuais
            contextual_suggestions = self._get_contextual_suggestions(conversation_context, user_profile)
            
            # 🔍 VALIDAR TIPOS DAS LISTAS DE SUGESTÕES
            # Garantir que todas as listas contêm apenas objetos Suggestion
            profile_suggestions = self._validate_suggestions_list(profile_suggestions, "profile")
            data_based_suggestions = self._validate_suggestions_list(data_based_suggestions, "data_based")
            contextual_suggestions = self._validate_suggestions_list(contextual_suggestions, "contextual")
            
            # Combinar todas as sugestões
            all_suggestions = profile_suggestions + data_based_suggestions + contextual_suggestions
            
            # Filtrar apenas objetos Suggestion válidos
            valid_suggestions = [s for s in all_suggestions if isinstance(s, Suggestion)]
            
            if len(valid_suggestions) != len(all_suggestions):
                logger.warning(f"⚠️ Filtradas {len(all_suggestions) - len(valid_suggestions)} sugestões inválidas")
            
            # Ordenar por prioridade
            prioritized = sorted(valid_suggestions, key=lambda x: x.priority, reverse=True)
            
            # Limitar a 6 sugestões principais
            final_suggestions = prioritized[:6]
            
            # Converter para dict
            result = []
            for s in final_suggestions:
                if isinstance(s, Suggestion):
                    result.append(s.to_dict())
                else:
                    # Fallback case - shouldn't happen
                    result.append({
                        "text": str(s),
                        "category": "unknown",
                        "priority": 1,
                        "icon": "❓",
                        "description": "Sugestão",
                        "user_profiles": [],
                        "context_keywords": []
                    })
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sugestões: {e}")
            # Retornar sugestões básicas em caso de erro
            return [
                {
                    "text": "Status do sistema",
                    "category": "basic",
                    "priority": 3,
                    "icon": "📊",
                    "description": "Verificar status geral do sistema",
                    "user_profiles": [user_context.get('perfil', 'usuario')]
                }
            ]
    
    def _validate_suggestions_list(self, suggestions_list: list, list_name: str) -> List[Suggestion]:
        """Valida e filtra lista de sugestões para garantir que são objetos Suggestion"""
        if not isinstance(suggestions_list, list):
            logger.warning(f"⚠️ {list_name}_suggestions não é lista: {type(suggestions_list)}")
            return []
        
        valid_suggestions = []
        for i, suggestion in enumerate(suggestions_list):
            if isinstance(suggestion, Suggestion):
                valid_suggestions.append(suggestion)
            else:
                logger.warning(f"⚠️ {list_name}_suggestions[{i}] não é Suggestion: {type(suggestion)}")
        
        return valid_suggestions
    
    def _generate_data_based_suggestions_simple(self, user_context: Dict[str, Any]) -> List[Suggestion]:
        """
        Versão simplificada de sugestões baseadas em dados (sem dependência externa)
        """
        suggestions = []
        user_profile = user_context.get('perfil', 'usuario').lower()
        vendedor_codigo = user_context.get('vendedor_codigo')
        
        # Sugestões específicas por perfil
        if user_profile == 'vendedor' and vendedor_codigo:
            suggestions.extend([
                Suggestion(
                    text="Meus clientes com entregas pendentes",
                    category="data_vendedor_pendentes",
                    priority=5,
                    icon="📋",
                    description="Verificar entregas pendentes da sua carteira",
                    user_profiles=["vendedor"],
                    context_keywords=["pendente", "carteira"]
                ),
                Suggestion(
                    text="Clientes que precisam de agendamento",
                    category="data_vendedor_agendamento",
                    priority=4,
                    icon="📅",
                    description="Clientes sem agendamento de entrega",
                    user_profiles=["vendedor"],
                    context_keywords=["agendamento", "sem data"]
                )
            ])
        
        elif user_profile in ['admin', 'financeiro']:
            suggestions.extend([
                Suggestion(
                    text="Relatório financeiro mensal",
                    category="data_financeiro_mensal",
                    priority=4,
                    icon="💰",
                    description="Análise financeira do mês atual",
                    user_profiles=["admin", "financeiro"],
                    context_keywords=["financeiro", "mensal"]
                ),
                Suggestion(
                    text="Faturas próximas do vencimento",
                    category="data_faturas_vencimento",
                    priority=5,
                    icon="⚠️",
                    description="Faturas que vencem nos próximos dias",
                    user_profiles=["admin", "financeiro"],
                    context_keywords=["fatura", "vencimento"]
                )
            ])
        
        elif user_profile in ['admin', 'operacional']:
            suggestions.extend([
                Suggestion(
                    text="Embarques aguardando liberação",
                    category="data_embarques_liberacao",
                    priority=5,
                    icon="🚛",
                    description="Embarques que precisam ser liberados",
                    user_profiles=["admin", "operacional"],
                    context_keywords=["embarque", "liberação"]
                ),
                Suggestion(
                    text="Entregas programadas para hoje",
                    category="data_entregas_hoje",
                    priority=4,
                    icon="📦",
                    description="Entregas agendadas para hoje",
                    user_profiles=["admin", "operacional", "vendedor"],
                    context_keywords=["entrega", "hoje", "programada"]
                )
            ])
        
        logger.debug(f"🧠 Geradas {len(suggestions)} sugestões simples para {user_profile}")
        return suggestions
    
    def _get_contextual_suggestions(self, conversation_context: Optional[Dict], user_profile: str) -> List[Suggestion]:
        """Gera sugestões baseadas no contexto da conversa atual"""
        if not conversation_context:
            return []
        
        contextual_suggestions = []
        
        # Verificar se há conversa recente sobre clientes específicos
        recent_content = conversation_context.get('recent_content', '').lower()
        
        # Se falou sobre um cliente específico, sugerir análises relacionadas
        if any(cliente in recent_content for cliente in ['assai', 'atacadão', 'carrefour', 'tenda']):
            for cliente in ['assai', 'atacadão', 'carrefour', 'tenda']:
                if cliente in recent_content:
                    contextual_suggestions.append(
                        Suggestion(
                            text=f"Histórico completo do {cliente.title()}",
                            category="contextual_cliente",
                            priority=5,
                            icon="📋",
                            description=f"Análise completa do cliente {cliente.title()}",
                            user_profiles=[user_profile, "admin"],
                            context_keywords=[cliente]
                        )
                    )
                    break
        
        return contextual_suggestions
    
    def _get_fallback_suggestions(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Sugestões de fallback em caso de erro"""
        try:
            # Validar user_context
            if not isinstance(user_context, dict):
                user_context = {'perfil': 'usuario'}
            
            profile = user_context.get('perfil', 'usuario').lower()
            
            fallback = [
                {
                    "text": "Status do sistema",
                    "category": "basic",
                    "priority": 3,
                    "icon": "📊",
                    "description": "Verificar status geral do sistema",
                    "user_profiles": [profile],
                    "context_keywords": []
                },
                {
                    "text": "Consultar entregas",
                    "category": "basic", 
                    "priority": 3,
                    "icon": "📦",
                    "description": "Consultar entregas recentes",
                    "user_profiles": [profile],
                    "context_keywords": []
                },
                {
                    "text": "Ajuda",
                    "category": "basic",
                    "priority": 2,
                    "icon": "❓",
                    "description": "Obter ajuda sobre o sistema",
                    "user_profiles": [profile],
                    "context_keywords": []
                }
            ]
            
            return fallback
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sugestões de fallback: {e}")
            # Fallback do fallback - sugestões mínimas
            return [
                {
                    "text": "Status do sistema",
                    "category": "basic",
                    "priority": 3,
                    "icon": "📊",
                    "description": "Verificar status geral do sistema",
                    "user_profiles": ["usuario"],
                    "context_keywords": []
                }
            ]
    
    def _generate_cache_key(self, user_context: Dict[str, Any], conversation_context: Optional[Dict] = None) -> str:
        """Gera chave única para cache de sugestões"""
        user_id = user_context.get('user_id', 'anonymous')
        profile = user_context.get('perfil', 'usuario')
        
        # Incluir hash do contexto conversacional se disponível
        context_hash = ""
        if conversation_context:
            context_str = str(conversation_context.get('recent_content', ''))[:50]  # Primeiros 50 chars
            context_hash = f"_{hash(context_str)}"
        
        return f"suggestions:{user_id}:{profile}{context_hash}"


# Instância global do engine de sugestões
suggestion_engine = None

def init_suggestion_engine(redis_cache=None):
    """Inicializa o engine de sugestões inteligentes"""
    global suggestion_engine
    try:
        suggestion_engine = SuggestionEngine(redis_cache)
        logger.info("🧠 Engine de Sugestões Inteligentes inicializado")
        return suggestion_engine
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar engine de sugestões: {e}")
        return None

def get_suggestion_engine():
    """Retorna instância do engine de sugestões"""
    return suggestion_engine 