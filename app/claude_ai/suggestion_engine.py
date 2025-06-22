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
    context_keywords: List[str] = None  # Palavras-chave que ativam esta sugestão
    
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
            # Cache key baseado no usuário e contexto
            cache_key = self._generate_cache_key(user_context, conversation_context)
            
            # Tentar buscar do cache Redis
            if self.redis_cache and self.redis_cache.disponivel:
                cached_suggestions = self.redis_cache.get(cache_key)
                if cached_suggestions:
                    logger.debug(f"🎯 Sugestões carregadas do cache para usuário {user_context.get('username', 'unknown')}")
                    return cached_suggestions
            
            # Gerar sugestões dinamicamente
            suggestions = self._generate_suggestions(user_context, conversation_context)
            
            # Salvar no cache
            if self.redis_cache and self.redis_cache.disponivel:
                self.redis_cache.set(cache_key, suggestions, ttl=self.cache_ttl)
                logger.debug(f"💾 Sugestões salvas no cache para usuário {user_context.get('username', 'unknown')}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sugestões inteligentes: {e}")
            return self._get_fallback_suggestions(user_context)
    
    def _generate_suggestions(self, user_context: Dict[str, Any], conversation_context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Gera sugestões baseadas no contexto atual"""
        
        user_profile = user_context.get('perfil', 'usuario').lower()
        username = user_context.get('username', 'Usuario')
        
        # Filtrar sugestões por perfil
        profile_suggestions = [
            s for s in self.base_suggestions 
            if user_profile in s.user_profiles or 'admin' in s.user_profiles
        ]
        
        # Analisar contexto conversacional para sugestões contextuais
        contextual_suggestions = self._get_contextual_suggestions(conversation_context, user_profile)
        
        # Combinar sugestões
        all_suggestions = profile_suggestions + contextual_suggestions
        
        # Ordenar por prioridade
        prioritized = sorted(all_suggestions, key=lambda x: x.priority, reverse=True)
        
        # Limitar a 6 sugestões principais
        final_suggestions = prioritized[:6]
        
        # Converter para dict
        return [s.to_dict() for s in final_suggestions]
    
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
        profile = user_context.get('perfil', 'usuario').lower()
        
        fallback = [
            {
                "text": "Status do sistema",
                "category": "basic",
                "priority": 3,
                "icon": "📊",
                "description": "Verificar status geral do sistema",
                "user_profiles": [profile]
            },
            {
                "text": "Consultar entregas",
                "category": "basic", 
                "priority": 3,
                "icon": "📦",
                "description": "Consultar entregas recentes",
                "user_profiles": [profile]
            },
            {
                "text": "Ajuda",
                "category": "basic",
                "priority": 2,
                "icon": "❓",
                "description": "Obter ajuda sobre o sistema",
                "user_profiles": [profile]
            }
        ]
        
        return fallback
    
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