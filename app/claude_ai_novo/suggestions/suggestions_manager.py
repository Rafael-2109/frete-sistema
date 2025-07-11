"""
💡 SUGGESTIONS MANAGER - Gerenciador de Sugestões
================================================

Módulo responsável por coordenar e gerenciar o sistema de sugestões inteligentes.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)

class SuggestionsManager:
    """
    Gerenciador central do sistema de sugestões.
    
    Responsabilidades:
    - Coordenar múltiplos engines de sugestão
    - Gerenciar contexto de sugestões
    - Filtrar e priorizar sugestões
    - Aprender com feedback
    - Cache de sugestões
    """
    
    def __init__(self):
        """Inicializa o gerenciador de sugestões."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("💡 SuggestionsManager inicializado")
        
        # Configurações do gerenciador
        self.config = {
            'max_suggestions': 10,
            'min_confidence': 0.3,
            'cache_ttl_minutes': 15,
            'learning_enabled': True,
            'feedback_weight': 0.8,
            'context_sensitivity': 0.7,
            'auto_prioritization': True
        }
        
        # Engines de sugestão registrados
        self.suggestion_engines = {}
        
        # Cache de sugestões
        self.suggestions_cache = {}
        
        # Histórico de feedback
        self.feedback_history = {}
        
        # Métricas de performance
        self.metrics = {
            'suggestions_generated': 0,
            'suggestions_accepted': 0,
            'suggestions_rejected': 0,
            'engines_active': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Contexto de sessão
        self.session_contexts = {}
        
        # Inicializar engines padrão
        self._initialize_default_engines()
    
    def generate_suggestions(self, context: Dict[str, Any], suggestion_type: str = 'general', **kwargs) -> Dict[str, Any]:
        """
        Gera sugestões baseadas no contexto.
        
        Args:
            context: Contexto para geração de sugestões
            suggestion_type: Tipo de sugestão ('general', 'query', 'action', 'optimization')
            **kwargs: Parâmetros adicionais
            
        Returns:
            Conjunto de sugestões geradas
        """
        try:
            result = {
                'timestamp': datetime.now().isoformat(),
                'suggestion_type': suggestion_type,
                'context_analyzed': True,
                'status': 'success',
                'suggestions': [],
                'confidence_scores': {},
                'sources': [],
                'metadata': {}
            }
            
            # Verificar cache primeiro
            cache_key = self._generate_cache_key(context, suggestion_type, kwargs)
            cached_suggestions = self._get_cached_suggestions(cache_key)
            
            if cached_suggestions:
                self.metrics['cache_hits'] += 1
                self.logger.debug(f"💾 Sugestões obtidas do cache: {cache_key[:20]}...")
                return cached_suggestions
            
            self.metrics['cache_misses'] += 1
            
            # Analisar contexto
            analyzed_context = self._analyze_context(context, suggestion_type, **kwargs)
            result['metadata']['context_analysis'] = analyzed_context
            
            # Gerar sugestões de múltiplos engines
            all_suggestions = []
            confidence_scores = {}
            sources_used = []
            
            # Iterar por engines ativos
            for engine_name, engine_info in self.suggestion_engines.items():
                if engine_info['active']:
                    try:
                        engine_suggestions = self._call_suggestion_engine(
                            engine_name, analyzed_context, suggestion_type, **kwargs
                        )
                        
                        if engine_suggestions:
                            all_suggestions.extend(engine_suggestions)
                            sources_used.append(engine_name)
                            
                            # Coletar scores de confiança
                            for suggestion in engine_suggestions:
                                suggestion_id = suggestion.get('id', f'{engine_name}_{len(all_suggestions)}')
                                confidence_scores[suggestion_id] = suggestion.get('confidence', 0.5)
                                
                    except Exception as e:
                        self.logger.warning(f"⚠️ Erro no engine {engine_name}: {e}")
                        engine_info['error_count'] += 1
            
            # Filtrar sugestões por confiança mínima
            filtered_suggestions = [
                s for s in all_suggestions 
                if s.get('confidence', 0.0) >= self.config['min_confidence']
            ]
            
            # Priorizar sugestões se habilitado
            if self.config['auto_prioritization']:
                prioritized_suggestions = self._prioritize_suggestions(
                    filtered_suggestions, analyzed_context, **kwargs
                )
            else:
                prioritized_suggestions = filtered_suggestions
            
            # Limitar número de sugestões
            final_suggestions = prioritized_suggestions[:self.config['max_suggestions']]
            
            # Enriquecer sugestões com metadados
            enriched_suggestions = self._enrich_suggestions(final_suggestions, analyzed_context)
            
            # Atualizar resultado
            result['suggestions'] = enriched_suggestions
            result['confidence_scores'] = confidence_scores
            result['sources'] = sources_used
            result['metadata']['total_generated'] = len(all_suggestions)
            result['metadata']['filtered_count'] = len(filtered_suggestions)
            result['metadata']['final_count'] = len(final_suggestions)
            
            # Cachear resultado
            self._cache_suggestions(cache_key, result)
            
            # Atualizar métricas
            self._update_metrics('generate', len(final_suggestions))
            
            self.logger.info(f"✅ Sugestões geradas: {len(final_suggestions)} de {len(all_suggestions)}, tipo: {suggestion_type}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar sugestões: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'suggestion_type': suggestion_type,
                'status': 'error',
                'error': str(e),
                'suggestions': []
            }
    
    def register_suggestion_engine(self, engine_name: str, engine_callable, priority: int = 5, config: Optional[Dict] = None) -> bool:
        """
        Registra um engine de sugestão.
        
        Args:
            engine_name: Nome do engine
            engine_callable: Função callable do engine
            priority: Prioridade (1-10, maior = mais importante)
            config: Configuração específica do engine
            
        Returns:
            True se registrado com sucesso
        """
        try:
            self.suggestion_engines[engine_name] = {
                'callable': engine_callable,
                'priority': priority,
                'config': config or {},
                'active': True,
                'registered_at': datetime.now().isoformat(),
                'call_count': 0,
                'error_count': 0,
                'success_rate': 1.0
            }
            
            self.metrics['engines_active'] = len([e for e in self.suggestion_engines.values() if e['active']])
            
            self.logger.info(f"✅ Engine '{engine_name}' registrado com prioridade {priority}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar engine '{engine_name}': {e}")
            return False
    
    def submit_feedback(self, suggestion_id: str, feedback_type: str, user_action: str, context: Optional[Dict] = None) -> bool:
        """
        Submete feedback sobre uma sugestão.
        
        Args:
            suggestion_id: ID da sugestão
            feedback_type: Tipo de feedback ('positive', 'negative', 'neutral')
            user_action: Ação do usuário ('accepted', 'rejected', 'ignored', 'modified')
            context: Contexto adicional
            
        Returns:
            True se feedback processado com sucesso
        """
        try:
            feedback_entry = {
                'suggestion_id': suggestion_id,
                'feedback_type': feedback_type,
                'user_action': user_action,
                'context': context or {},
                'timestamp': datetime.now().isoformat(),
                'processed': False
            }
            
            # Armazenar feedback
            if suggestion_id not in self.feedback_history:
                self.feedback_history[suggestion_id] = []
            
            self.feedback_history[suggestion_id].append(feedback_entry)
            
            # Processar feedback se aprendizado habilitado
            if self.config['learning_enabled']:
                self._process_feedback(feedback_entry)
            
            # Atualizar métricas
            if user_action == 'accepted':
                self.metrics['suggestions_accepted'] += 1
            elif user_action == 'rejected':
                self.metrics['suggestions_rejected'] += 1
            
            self.logger.info(f"✅ Feedback processado: {suggestion_id} - {feedback_type}/{user_action}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar feedback: {e}")
            return False
    
    def get_suggestion_recommendations(self, user_profile: Dict[str, Any], session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtém recomendações de sugestões baseadas no perfil do usuário.
        
        Args:
            user_profile: Perfil do usuário
            session_context: Contexto da sessão
            
        Returns:
            Recomendações personalizadas
        """
        try:
            recommendations = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_profile.get('user_id', 'anonymous'),
                'personalized_suggestions': [],
                'trending_suggestions': [],
                'contextual_suggestions': [],
                'quick_actions': []
            }
            
            # Gerar sugestões personalizadas
            personalized = self._generate_personalized_suggestions(user_profile, session_context)
            recommendations['personalized_suggestions'] = personalized
            
            # Gerar sugestões em alta
            trending = self._generate_trending_suggestions(session_context)
            recommendations['trending_suggestions'] = trending
            
            # Gerar sugestões contextuais
            contextual = self._generate_contextual_suggestions(session_context)
            recommendations['contextual_suggestions'] = contextual
            
            # Gerar ações rápidas
            quick_actions = self._generate_quick_actions(user_profile, session_context)
            recommendations['quick_actions'] = quick_actions
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar recomendações: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'personalized_suggestions': [],
                'trending_suggestions': [],
                'contextual_suggestions': [],
                'quick_actions': []
            }
    
    def optimize_suggestion_performance(self) -> Dict[str, Any]:
        """
        Otimiza performance do sistema de sugestões.
        
        Returns:
            Relatório de otimização
        """
        try:
            optimization_report = {
                'timestamp': datetime.now().isoformat(),
                'actions_taken': [],
                'performance_improvements': {},
                'engine_adjustments': {},
                'cache_optimization': {}
            }
            
            # Otimizar engines baseado em performance
            engine_optimizations = self._optimize_engines()
            optimization_report['engine_adjustments'] = engine_optimizations
            
            # Otimizar cache
            cache_optimizations = self._optimize_cache()
            optimization_report['cache_optimization'] = cache_optimizations
            
            # Ajustar configurações baseado em métricas
            config_adjustments = self._adjust_configurations()
            optimization_report['config_adjustments'] = config_adjustments
            
            # Limpar dados antigos
            cleanup_results = self._cleanup_old_data()
            optimization_report['cleanup_results'] = cleanup_results
            
            self.logger.info("🔧 Otimização do sistema de sugestões concluída")
            
            return optimization_report
            
        except Exception as e:
            self.logger.error(f"❌ Erro na otimização: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'actions_taken': []
            }
    
    def _initialize_default_engines(self):
        """Inicializa engines padrão."""
        # Engine de sugestões contextuais
        self.register_suggestion_engine(
            'contextual_engine',
            self._contextual_suggestions_engine,
            priority=8
        )
        
        # Engine de sugestões baseadas em histórico
        self.register_suggestion_engine(
            'history_engine',
            self._history_based_engine,
            priority=6
        )
        
        # Engine de sugestões por popularidade
        self.register_suggestion_engine(
            'popularity_engine',
            self._popularity_based_engine,
            priority=4
        )
    
    def _analyze_context(self, context: Dict[str, Any], suggestion_type: str, **kwargs) -> Dict[str, Any]:
        """Analisa contexto para geração de sugestões."""
        analyzed = {
            'original_context': context,
            'suggestion_type': suggestion_type,
            'context_features': {},
            'priority_factors': [],
            'user_indicators': {},
            'temporal_factors': {}
        }
        
        # Extrair características do contexto
        if 'query' in context:
            analyzed['context_features']['has_query'] = True
            analyzed['context_features']['query_length'] = len(str(context['query']))
            analyzed['context_features']['query_complexity'] = self._assess_query_complexity(context['query'])
        
        if 'user_id' in context:
            analyzed['user_indicators']['user_id'] = context['user_id']
            analyzed['user_indicators']['has_history'] = self._user_has_history(context['user_id'])
        
        # Fatores temporais
        analyzed['temporal_factors']['hour'] = datetime.now().hour
        analyzed['temporal_factors']['day_of_week'] = datetime.now().weekday()
        
        return analyzed
    
    def _call_suggestion_engine(self, engine_name: str, context: Dict[str, Any], suggestion_type: str, **kwargs) -> List[Dict[str, Any]]:
        """Chama um engine de sugestão específico."""
        engine_info = self.suggestion_engines[engine_name]
        engine_callable = engine_info['callable']
        
        # Incrementar contador
        engine_info['call_count'] += 1
        
        try:
            suggestions = engine_callable(context, suggestion_type, **kwargs)
            
            # Atualizar taxa de sucesso
            total_calls = engine_info['call_count']
            error_calls = engine_info['error_count']
            engine_info['success_rate'] = (total_calls - error_calls) / total_calls
            
            return suggestions or []
            
        except Exception as e:
            engine_info['error_count'] += 1
            total_calls = engine_info['call_count']
            error_calls = engine_info['error_count']
            engine_info['success_rate'] = (total_calls - error_calls) / total_calls
            raise e
    
    def _prioritize_suggestions(self, suggestions: List[Dict[str, Any]], context: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """Prioriza sugestões baseado em múltiplos fatores."""
        # Calcular score de prioridade para cada sugestão
        for suggestion in suggestions:
            priority_score = 0.0
            
            # Score baseado em confiança
            confidence = suggestion.get('confidence', 0.5)
            priority_score += confidence * 0.4
            
            # Score baseado em relevância contextual
            relevance = self._calculate_contextual_relevance(suggestion, context)
            priority_score += relevance * 0.3
            
            # Score baseado em feedback histórico
            historical_score = self._get_historical_score(suggestion)
            priority_score += historical_score * 0.2
            
            # Score baseado na fonte
            source_score = self._get_source_score(suggestion)
            priority_score += source_score * 0.1
            
            suggestion['priority_score'] = priority_score
        
        # Ordenar por score de prioridade
        return sorted(suggestions, key=lambda x: x.get('priority_score', 0.0), reverse=True)
    
    def _enrich_suggestions(self, suggestions: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enriquece sugestões com metadados adicionais."""
        enriched = []
        
        for i, suggestion in enumerate(suggestions):
            enriched_suggestion = suggestion.copy()
            
            # Adicionar ID único se não existir
            if 'id' not in enriched_suggestion:
                enriched_suggestion['id'] = f"suggestion_{i}_{datetime.now().timestamp()}"
            
            # Adicionar timestamp
            enriched_suggestion['generated_at'] = datetime.now().isoformat()
            
            # Adicionar categoria
            if 'category' not in enriched_suggestion:
                enriched_suggestion['category'] = self._categorize_suggestion(enriched_suggestion)
            
            # Adicionar explicação se não existir
            if 'explanation' not in enriched_suggestion:
                enriched_suggestion['explanation'] = self._generate_explanation(enriched_suggestion, context)
            
            # Adicionar indicadores de ação
            enriched_suggestion['action_required'] = self._requires_immediate_action(enriched_suggestion)
            enriched_suggestion['complexity'] = self._assess_suggestion_complexity(enriched_suggestion)
            
            enriched.append(enriched_suggestion)
        
        return enriched
    
    def _generate_cache_key(self, context: Dict[str, Any], suggestion_type: str, kwargs: Dict[str, Any]) -> str:
        """Gera chave de cache."""
        content = f"{str(context)}|{suggestion_type}|{str(sorted(kwargs.items()))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_suggestions(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Obtém sugestões do cache."""
        if cache_key not in self.suggestions_cache:
            return None
        
        cache_entry = self.suggestions_cache[cache_key]
        
        # Verificar TTL
        cached_at = datetime.fromisoformat(cache_entry['cached_at'])
        age = datetime.now() - cached_at
        
        if age > timedelta(minutes=self.config['cache_ttl_minutes']):
            del self.suggestions_cache[cache_key]
            return None
        
        return cache_entry['data']
    
    def _cache_suggestions(self, cache_key: str, suggestions: Dict[str, Any]):
        """Armazena sugestões no cache."""
        cache_entry = {
            'data': suggestions,
            'cached_at': datetime.now().isoformat()
        }
        
        self.suggestions_cache[cache_key] = cache_entry
    
    def _process_feedback(self, feedback_entry: Dict[str, Any]):
        """Processa feedback para aprendizado."""
        suggestion_id = feedback_entry['suggestion_id']
        feedback_type = feedback_entry['feedback_type']
        user_action = feedback_entry['user_action']
        
        # Lógica de aprendizado simplificada
        weight = self.config['feedback_weight']
        
        if feedback_type == 'positive' and user_action == 'accepted':
            # Aumentar confiança em sugestões similares
            self._boost_similar_suggestions(suggestion_id, weight)
        elif feedback_type == 'negative' and user_action == 'rejected':
            # Diminuir confiança em sugestões similares
            self._decrease_similar_suggestions(suggestion_id, weight)
        
        feedback_entry['processed'] = True
    
    def _update_metrics(self, operation: str, count: int = 1):
        """Atualiza métricas do sistema."""
        if operation == 'generate':
            self.metrics['suggestions_generated'] += count
    
    # Engines de sugestão padrão
    def _contextual_suggestions_engine(self, context: Dict[str, Any], suggestion_type: str, **kwargs) -> List[Dict[str, Any]]:
        """Engine de sugestões contextuais."""
        suggestions = []
        
        # Sugestões baseadas no tipo
        if suggestion_type == 'query':
            suggestions.extend([
                {
                    'text': 'Refinar consulta com filtros específicos',
                    'type': 'refinement',
                    'confidence': 0.8,
                    'category': 'optimization'
                },
                {
                    'text': 'Exportar resultados para Excel',
                    'type': 'action',
                    'confidence': 0.7,
                    'category': 'export'
                }
            ])
        elif suggestion_type == 'general':
            suggestions.extend([
                {
                    'text': 'Visualizar dashboard executivo',
                    'type': 'navigation',
                    'confidence': 0.6,
                    'category': 'analytics'
                },
                {
                    'text': 'Consultar entregas pendentes',
                    'type': 'query',
                    'confidence': 0.8,
                    'category': 'monitoring'
                }
            ])
        
        return suggestions
    
    def _history_based_engine(self, context: Dict[str, Any], suggestion_type: str, **kwargs) -> List[Dict[str, Any]]:
        """Engine baseado em histórico."""
        return [
            {
                'text': 'Repetir consulta anterior bem-sucedida',
                'type': 'repeat',
                'confidence': 0.9,
                'category': 'history'
            }
        ]
    
    def _popularity_based_engine(self, context: Dict[str, Any], suggestion_type: str, **kwargs) -> List[Dict[str, Any]]:
        """Engine baseado em popularidade."""
        return [
            {
                'text': 'Consulta mais popular: Status das entregas',
                'type': 'popular',
                'confidence': 0.7,
                'category': 'trending'
            }
        ]
    
    # Métodos auxiliares
    def _assess_query_complexity(self, query: str) -> str:
        """Avalia complexidade da consulta."""
        word_count = len(str(query).split())
        if word_count <= 3:
            return 'simple'
        elif word_count <= 8:
            return 'medium'
        else:
            return 'complex'
    
    def _user_has_history(self, user_id: str) -> bool:
        """Verifica se usuário tem histórico."""
        return user_id in self.feedback_history
    
    def _calculate_contextual_relevance(self, suggestion: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calcula relevância contextual."""
        return 0.7  # Placeholder
    
    def _get_historical_score(self, suggestion: Dict[str, Any]) -> float:
        """Obtém score baseado em histórico."""
        return 0.6  # Placeholder
    
    def _get_source_score(self, suggestion: Dict[str, Any]) -> float:
        """Obtém score da fonte."""
        return 0.5  # Placeholder
    
    def _categorize_suggestion(self, suggestion: Dict[str, Any]) -> str:
        """Categoriza sugestão."""
        return suggestion.get('category', 'general')
    
    def _generate_explanation(self, suggestion: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Gera explicação para a sugestão."""
        return f"Sugerido baseado no contexto atual: {suggestion.get('type', 'ação')}"
    
    def _requires_immediate_action(self, suggestion: Dict[str, Any]) -> bool:
        """Verifica se requer ação imediata."""
        return suggestion.get('type') == 'action'
    
    def _assess_suggestion_complexity(self, suggestion: Dict[str, Any]) -> str:
        """Avalia complexidade da sugestão."""
        return 'medium'  # Placeholder
    
    def _boost_similar_suggestions(self, suggestion_id: str, weight: float):
        """Aumenta confiança em sugestões similares."""
        pass  # Placeholder para aprendizado
    
    def _decrease_similar_suggestions(self, suggestion_id: str, weight: float):
        """Diminui confiança em sugestões similares."""
        pass  # Placeholder para aprendizado
    
    def _generate_personalized_suggestions(self, user_profile: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gera sugestões personalizadas."""
        return [
            {
                'text': f"Consulta personalizada para {user_profile.get('role', 'usuário')}",
                'type': 'personalized',
                'confidence': 0.8
            }
        ]
    
    def _generate_trending_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gera sugestões em alta."""
        return [
            {
                'text': 'Análise de tendências de entrega',
                'type': 'trending',
                'confidence': 0.7
            }
        ]
    
    def _generate_contextual_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gera sugestões contextuais."""
        return [
            {
                'text': 'Ação contextual baseada na sessão atual',
                'type': 'contextual',
                'confidence': 0.8
            }
        ]
    
    def _generate_quick_actions(self, user_profile: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gera ações rápidas."""
        return [
            {
                'text': 'Acesso rápido ao dashboard',
                'type': 'quick_action',
                'confidence': 0.9
            }
        ]
    
    def _optimize_engines(self) -> Dict[str, Any]:
        """Otimiza engines baseado em performance."""
        optimizations = {}
        
        for engine_name, engine_info in self.suggestion_engines.items():
            success_rate = engine_info['success_rate']
            
            if success_rate < 0.7:
                # Desativar engines com baixa performance
                engine_info['active'] = False
                optimizations[engine_name] = 'deactivated_low_performance'
            elif success_rate > 0.9:
                # Aumentar prioridade de engines com alta performance
                engine_info['priority'] = min(engine_info['priority'] + 1, 10)
                optimizations[engine_name] = 'priority_increased'
        
        return optimizations
    
    def _optimize_cache(self) -> Dict[str, Any]:
        """Otimiza cache de sugestões."""
        cache_size_before = len(self.suggestions_cache)
        
        # Remover entradas expiradas
        expired_keys = []
        now = datetime.now()
        
        for cache_key, cache_entry in self.suggestions_cache.items():
            cached_at = datetime.fromisoformat(cache_entry['cached_at'])
            age = now - cached_at
            
            if age > timedelta(minutes=self.config['cache_ttl_minutes']):
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.suggestions_cache[key]
        
        cache_size_after = len(self.suggestions_cache)
        
        return {
            'entries_before': cache_size_before,
            'entries_after': cache_size_after,
            'entries_removed': len(expired_keys)
        }
    
    def _adjust_configurations(self) -> Dict[str, Any]:
        """Ajusta configurações baseado em métricas."""
        adjustments = {}
        
        # Ajustar threshold de confiança baseado na taxa de aceitação
        if self.metrics['suggestions_generated'] > 0:
            acceptance_rate = self.metrics['suggestions_accepted'] / self.metrics['suggestions_generated']
            
            if acceptance_rate < 0.3:
                # Aumentar threshold se taxa de aceitação baixa
                old_threshold = self.config['min_confidence']
                self.config['min_confidence'] = min(old_threshold + 0.1, 0.8)
                adjustments['min_confidence'] = f"increased from {old_threshold} to {self.config['min_confidence']}"
            elif acceptance_rate > 0.8:
                # Diminuir threshold se taxa de aceitação alta
                old_threshold = self.config['min_confidence']
                self.config['min_confidence'] = max(old_threshold - 0.1, 0.2)
                adjustments['min_confidence'] = f"decreased from {old_threshold} to {self.config['min_confidence']}"
        
        return adjustments
    
    def _cleanup_old_data(self) -> Dict[str, Any]:
        """Limpa dados antigos."""
        cleanup_results = {
            'feedback_entries_removed': 0,
            'cache_entries_removed': 0
        }
        
        # Limpar feedback muito antigo (mais de 30 dias)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for suggestion_id, feedback_list in list(self.feedback_history.items()):
            filtered_feedback = [
                fb for fb in feedback_list
                if datetime.fromisoformat(fb['timestamp']) > cutoff_date
            ]
            
            removed_count = len(feedback_list) - len(filtered_feedback)
            cleanup_results['feedback_entries_removed'] += removed_count
            
            if filtered_feedback:
                self.feedback_history[suggestion_id] = filtered_feedback
            else:
                del self.feedback_history[suggestion_id]
        
        return cleanup_results


def get_suggestions_manager() -> SuggestionsManager:
    """
    Obtém instância do gerenciador de sugestões.
    
    Returns:
        Instância do SuggestionsManager
    """
    return SuggestionsManager()
