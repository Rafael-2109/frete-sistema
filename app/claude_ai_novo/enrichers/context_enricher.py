"""
Context Enricher - Enriquecedor de Contexto
Responsabilidade: ENRIQUECER contexto com informações adicionais
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .performance_cache import cached_result, performance_monitor

logger = logging.getLogger(__name__)

class ContextEnricher:
    """
    Enriquecedor de contexto para melhorar análise de consultas.
    
    Responsabilidades:
    - Enriquecer contexto conversacional
    - Adicionar informações contextuais
    - Melhorar compreensão de consultas
    """
    
    def __init__(self, context_manager=None):
        """
        Inicializa o enriquecedor de contexto.
        
        Args:
            context_manager: Manager de contexto (opcional)
        """
        self.context_manager = context_manager
        self.enrichment_cache = {}
        
        logger.info("🔍 ContextEnricher inicializado")
    
    @performance_monitor
    def enrich_context(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enriquece contexto para uma consulta.
        
        Args:
            query: Consulta do usuário
            context: Contexto atual (opcional)
            
        Returns:
            Dict com contexto enriquecido
        """
        if context is None:
            context = {}
        
        enriched_context = {
            'original_query': query,
            'timestamp': datetime.now().isoformat(),
            'enrichments': {},
            'context_score': 0.0
        }
        
        # Copiar contexto original
        enriched_context.update(context)
        
        # Aplicar diferentes tipos de enriquecimento
        enriched_context['enrichments'] = {
            'temporal': self._enrich_temporal_context(query, context),
            'semantic': self._enrich_semantic_context(query, context),
            'conversational': self._enrich_conversational_context(query, context),
            'domain': self._enrich_domain_context(query, context)
        }
        
        # Calcular score geral do contexto
        enriched_context['context_score'] = self._calculate_context_score(enriched_context)
        
        logger.info(f"Contexto enriquecido - Score: {enriched_context['context_score']:.2f}")
        
        return enriched_context
    
    def _enrich_temporal_context(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece contexto temporal.
        
        Args:
            query: Consulta
            context: Contexto atual
            
        Returns:
            Dict com informações temporais
        """
        temporal_info = {
            'query_time': datetime.now().isoformat(),
            'detected_periods': [],
            'time_relevance': 0.0
        }
        
        # Detectar referências temporais na consulta
        time_keywords = [
            'hoje', 'ontem', 'amanhã', 'semana', 'mês', 'ano',
            'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
            'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
        ]
        
        query_lower = query.lower()
        detected_periods = [kw for kw in time_keywords if kw in query_lower]
        
        if detected_periods:
            temporal_info['detected_periods'] = detected_periods
            temporal_info['time_relevance'] = min(len(detected_periods) * 0.3, 1.0)
        
        return temporal_info
    
    def _enrich_semantic_context(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece contexto semântico.
        
        Args:
            query: Consulta
            context: Contexto atual
            
        Returns:
            Dict com informações semânticas
        """
        semantic_info = {
            'query_intent': 'unknown',
            'confidence': 0.0,
            'entities': [],
            'semantic_similarity': 0.0
        }
        
        # Detectar intenção básica
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['quantos', 'quanto', 'qual', 'quais']):
            semantic_info['query_intent'] = 'question'
            semantic_info['confidence'] = 0.8
        elif any(word in query_lower for word in ['listar', 'mostrar', 'exibir']):
            semantic_info['query_intent'] = 'list'
            semantic_info['confidence'] = 0.7
        elif any(word in query_lower for word in ['relatório', 'excel', 'exportar']):
            semantic_info['query_intent'] = 'export'
            semantic_info['confidence'] = 0.9
        
        # Detectar entidades básicas
        entities = []
        entity_keywords = {
            'cliente': ['cliente', 'clientes'],
            'produto': ['produto', 'produtos'],
            'entrega': ['entrega', 'entregas'],
            'pedido': ['pedido', 'pedidos'],
            'frete': ['frete', 'fretes']
        }
        
        for entity_type, keywords in entity_keywords.items():
            if any(kw in query_lower for kw in keywords):
                entities.append(entity_type)
        
        semantic_info['entities'] = entities
        
        return semantic_info
    
    def _enrich_conversational_context(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece contexto conversacional.
        
        Args:
            query: Consulta
            context: Contexto atual
            
        Returns:
            Dict com informações conversacionais
        """
        conversational_info = {
            'is_followup': False,
            'reference_resolution': [],
            'conversation_flow': 'new'
        }
        
        # Detectar perguntas de seguimento
        query_lower = query.lower()
        followup_indicators = ['e', 'também', 'além', 'ainda', 'mais']
        
        if any(indicator in query_lower for indicator in followup_indicators):
            conversational_info['is_followup'] = True
            conversational_info['conversation_flow'] = 'continuation'
        
        # Detectar referências pronominais
        pronouns = ['ele', 'ela', 'isso', 'aquele', 'aquela', 'este', 'esta']
        references = [pron for pron in pronouns if pron in query_lower]
        
        if references:
            conversational_info['reference_resolution'] = references
        
        return conversational_info
    
    def _enrich_domain_context(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece contexto de domínio específico.
        
        Args:
            query: Consulta
            context: Contexto atual
            
        Returns:
            Dict com informações de domínio
        """
        domain_info = {
            'domain_detected': [],
            'business_context': {},
            'domain_relevance': 0.0
        }
        
        # Detectar domínios específicos
        domain_keywords = {
            'logistica': ['frete', 'entrega', 'transportadora', 'embarque'],
            'vendas': ['pedido', 'cliente', 'cotação', 'venda'],
            'financeiro': ['faturamento', 'pagamento', 'valor', 'custo'],
            'operacional': ['produção', 'estoque', 'separação', 'expedição']
        }
        
        query_lower = query.lower()
        detected_domains = []
        
        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_domains.append(domain)
        
        domain_info['domain_detected'] = detected_domains
        
        # Calcular relevância do domínio
        if detected_domains:
            domain_info['domain_relevance'] = min(len(detected_domains) * 0.4, 1.0)
        
        return domain_info
    
    def _calculate_context_score(self, enriched_context: Dict[str, Any]) -> float:
        """
        Calcula score geral do contexto enriquecido.
        
        Args:
            enriched_context: Contexto enriquecido
            
        Returns:
            Score entre 0.0 e 1.0
        """
        score = 0.0
        enrichments = enriched_context.get('enrichments', {})
        
        # Pontuação temporal
        temporal = enrichments.get('temporal', {})
        score += temporal.get('time_relevance', 0.0) * 0.2
        
        # Pontuação semântica
        semantic = enrichments.get('semantic', {})
        score += semantic.get('confidence', 0.0) * 0.4
        
        # Pontuação conversacional
        conversational = enrichments.get('conversational', {})
        if conversational.get('is_followup'):
            score += 0.2
        
        # Pontuação de domínio
        domain = enrichments.get('domain', {})
        score += domain.get('domain_relevance', 0.0) * 0.2
        
        return min(score, 1.0)
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do enriquecimento de contexto.
        
        Returns:
            Dict com estatísticas
        """
        cache_key = f"context_stats_{id(self)}"
        return cached_result(cache_key, self._get_context_stats)
    
    def _get_context_stats(self) -> Dict[str, Any]:
        """
        Calcula estatísticas internas.
        
        Returns:
            Dict com estatísticas
        """
        return {
            'total_enrichments': len(self.enrichment_cache),
            'average_score': 0.75,  # Placeholder
            'most_common_domains': ['logistica', 'vendas'],
            'timestamp': datetime.now().isoformat()
        }

# Função de conveniência
def get_context_enricher() -> ContextEnricher:
    """
    Retorna instância configurada do ContextEnricher.
    
    Returns:
        ContextEnricher configurado
    """
    return ContextEnricher() 