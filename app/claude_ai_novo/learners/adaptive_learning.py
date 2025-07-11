"""
🎓 ADAPTIVE LEARNING - Aprendizado Adaptativo
===========================================

Módulo responsável por aprendizado adaptativo e personalização dinâmica.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)

class AdaptiveLearning:
    """
    Sistema de aprendizado adaptativo que se ajusta com base no comportamento do usuário.
    
    Responsabilidades:
    - Aprendizado contínuo do comportamento do usuário
    - Adaptação de respostas baseada em feedback
    - Personalização de sugestões
    - Otimização de performance
    - Detecção de padrões de uso
    """
    
    def __init__(self):
        """Inicializa o sistema de aprendizado adaptativo."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("🎓 AdaptiveLearning inicializado")
        
        # Armazenamento de aprendizado em memória
        self.user_profiles = {}
        self.interaction_history = []
        self.learning_patterns = {}
        self.adaptation_rules = {}
        
        # Configurações de aprendizado
        self.config = {
            'learning_rate': 0.1,
            'min_interactions': 5,
            'pattern_threshold': 0.7,
            'adaptation_threshold': 0.6,
            'max_history_size': 1000
        }
        
        # Inicializar regras de adaptação padrão
        self._initialize_adaptation_rules()
    
    def learn_from_interaction(self, user_id: str, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aprende com uma interação do usuário.
        
        Args:
            user_id: ID do usuário
            interaction_data: Dados da interação
            
        Returns:
            Resultado do aprendizado
        """
        try:
            learning_result = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'learning_type': 'interaction',
                'status': 'success',
                'patterns_detected': [],
                'adaptations_made': [],
                'confidence': 0.0
            }
            
            # Registrar interação
            self._record_interaction(user_id, interaction_data)
            
            # Atualizar perfil do usuário
            self._update_user_profile(user_id, interaction_data)
            
            # Detectar padrões
            patterns = self._detect_patterns(user_id)
            learning_result['patterns_detected'] = patterns
            
            # Aplicar adaptações
            adaptations = self._apply_adaptations(user_id, patterns)
            learning_result['adaptations_made'] = adaptations
            
            # Calcular confiança
            learning_result['confidence'] = self._calculate_learning_confidence(user_id)
            
            return learning_result
            
        except Exception as e:
            self.logger.error(f"❌ Erro no aprendizado da interação: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'learning_type': 'interaction',
                'status': 'error',
                'error': str(e),
                'confidence': 0.0
            }
    
    def get_personalized_recommendations(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Gera recomendações personalizadas para o usuário.
        
        Args:
            user_id: ID do usuário
            context: Contexto atual
            
        Returns:
            Lista de recomendações personalizadas
        """
        try:
            recommendations = []
            
            # Obter perfil do usuário
            profile = self.user_profiles.get(user_id, {})
            
            if not profile:
                return self._get_default_recommendations(context)
            
            # Gerar recomendações baseadas no perfil
            preferences = profile.get('preferences', {})
            patterns = profile.get('patterns', [])
            
            # Recomendações baseadas em preferências
            for preference_type, preference_data in preferences.items():
                recommendations.extend(
                    self._generate_preference_recommendations(preference_type, preference_data, context)
                )
            
            # Recomendações baseadas em padrões
            for pattern in patterns:
                recommendations.extend(
                    self._generate_pattern_recommendations(pattern, context)
                )
            
            # Ordenar por relevância
            recommendations = self._rank_recommendations(recommendations, profile)
            
            return recommendations[:10]  # Limitar a 10 recomendações
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar recomendações: {e}")
            return self._get_default_recommendations(context)
    
    def adapt_response(self, user_id: str, original_response: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Adapta uma resposta baseada no perfil do usuário.
        
        Args:
            user_id: ID do usuário
            original_response: Resposta original
            context: Contexto da resposta
            
        Returns:
            Resposta adaptada
        """
        try:
            adapted_response = original_response.copy()
            adapted_response['adaptations_applied'] = []
            
            # Obter perfil do usuário
            profile = self.user_profiles.get(user_id, {})
            
            if not profile:
                return adapted_response
            
            # Aplicar adaptações baseadas no perfil
            preferences = profile.get('preferences', {})
            
            # Adaptar nível de detalhe
            if 'detail_level' in preferences:
                adapted_response = self._adapt_detail_level(
                    adapted_response, preferences['detail_level']
                )
            
            # Adaptar formato de apresentação
            if 'presentation_format' in preferences:
                adapted_response = self._adapt_presentation_format(
                    adapted_response, preferences['presentation_format']
                )
            
            # Adaptar linguagem
            if 'language_style' in preferences:
                adapted_response = self._adapt_language_style(
                    adapted_response, preferences['language_style']
                )
            
            return adapted_response
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao adaptar resposta: {e}")
            return original_response
    
    def update_learning_from_feedback(self, user_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza o aprendizado baseado em feedback do usuário.
        
        Args:
            user_id: ID do usuário
            feedback: Feedback do usuário
            
        Returns:
            Resultado da atualização
        """
        try:
            update_result = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'feedback_type': feedback.get('type', 'general'),
                'adjustments_made': [],
                'status': 'success'
            }
            
            # Processar feedback
            feedback_score = feedback.get('score', 0)
            feedback_text = feedback.get('text', '')
            
            # Ajustar perfil baseado no feedback
            profile = self.user_profiles.get(user_id, {})
            
            if feedback_score < 3:  # Feedback negativo
                adjustments = self._handle_negative_feedback(user_id, feedback, profile)
                update_result['adjustments_made'].extend(adjustments)
            elif feedback_score > 7:  # Feedback positivo
                adjustments = self._handle_positive_feedback(user_id, feedback, profile)
                update_result['adjustments_made'].extend(adjustments)
            
            # Atualizar perfil
            self.user_profiles[user_id] = profile
            
            return update_result
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar aprendizado: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'status': 'error',
                'error': str(e)
            }
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Obtém perfil do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Perfil do usuário
        """
        return self.user_profiles.get(user_id, {})
    
    def _initialize_adaptation_rules(self):
        """Inicializa regras de adaptação padrão."""
        self.adaptation_rules = {
            'detail_level': {
                'high': {'threshold': 0.8, 'action': 'increase_detail'},
                'low': {'threshold': 0.3, 'action': 'decrease_detail'}
            },
            'response_speed': {
                'fast': {'threshold': 0.7, 'action': 'prioritize_speed'},
                'thorough': {'threshold': 0.7, 'action': 'prioritize_accuracy'}
            },
            'language_style': {
                'technical': {'threshold': 0.6, 'action': 'use_technical_terms'},
                'simple': {'threshold': 0.6, 'action': 'simplify_language'}
            }
        }
    
    def _record_interaction(self, user_id: str, interaction_data: Dict[str, Any]):
        """Registra interação do usuário."""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'data': interaction_data
        }
        
        self.interaction_history.append(interaction)
        
        # Limitar tamanho do histórico
        if len(self.interaction_history) > self.config['max_history_size']:
            self.interaction_history = self.interaction_history[-self.config['max_history_size']:]
    
    def _update_user_profile(self, user_id: str, interaction_data: Dict[str, Any]):
        """Atualiza perfil do usuário."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'created_at': datetime.now().isoformat(),
                'interactions_count': 0,
                'preferences': {},
                'patterns': [],
                'last_updated': datetime.now().isoformat()
            }
        
        profile = self.user_profiles[user_id]
        profile['interactions_count'] += 1
        profile['last_updated'] = datetime.now().isoformat()
        
        # Extrair preferências da interação
        self._extract_preferences(profile, interaction_data)
    
    def _extract_preferences(self, profile: Dict[str, Any], interaction_data: Dict[str, Any]):
        """Extrai preferências da interação."""
        preferences = profile.get('preferences', {})
        
        # Analisar tipo de consulta
        query_type = interaction_data.get('query_type', 'general')
        if 'query_types' not in preferences:
            preferences['query_types'] = {}
        preferences['query_types'][query_type] = preferences['query_types'].get(query_type, 0) + 1
        
        # Analisar tempo de resposta esperado
        response_time = interaction_data.get('response_time', 0)
        if response_time > 0:
            if 'avg_response_time' not in preferences:
                preferences['avg_response_time'] = response_time
            else:
                preferences['avg_response_time'] = (
                    preferences['avg_response_time'] * 0.8 + response_time * 0.2
                )
        
        profile['preferences'] = preferences
    
    def _detect_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Detecta padrões no comportamento do usuário."""
        patterns = []
        
        # Obter interações do usuário
        user_interactions = [
            interaction for interaction in self.interaction_history
            if interaction['user_id'] == user_id
        ]
        
        if len(user_interactions) < self.config['min_interactions']:
            return patterns
        
        # Detectar padrões de horário
        time_pattern = self._detect_time_pattern(user_interactions)
        if time_pattern:
            patterns.append(time_pattern)
        
        # Detectar padrões de consulta
        query_pattern = self._detect_query_pattern(user_interactions)
        if query_pattern:
            patterns.append(query_pattern)
        
        return patterns
    
    def _detect_time_pattern(self, interactions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detecta padrões de horário."""
        hours = []
        for interaction in interactions:
            timestamp = datetime.fromisoformat(interaction['timestamp'])
            hours.append(timestamp.hour)
        
        if len(hours) < 3:
            return None
        
        # Encontrar horário mais comum
        from collections import Counter
        hour_counts = Counter(hours)
        most_common_hour = hour_counts.most_common(1)[0]
        
        if most_common_hour[1] >= len(hours) * 0.3:  # 30% das interações
            return {
                'type': 'time_pattern',
                'pattern': 'frequent_hour',
                'data': {'hour': most_common_hour[0]},
                'confidence': most_common_hour[1] / len(hours)
            }
        
        return None
    
    def _detect_query_pattern(self, interactions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detecta padrões de consulta."""
        query_types = []
        for interaction in interactions:
            query_type = interaction.get('data', {}).get('query_type', 'general')
            query_types.append(query_type)
        
        if len(query_types) < 3:
            return None
        
        # Encontrar tipo de consulta mais comum
        from collections import Counter
        type_counts = Counter(query_types)
        most_common_type = type_counts.most_common(1)[0]
        
        if most_common_type[1] >= len(query_types) * 0.4:  # 40% das consultas
            return {
                'type': 'query_pattern',
                'pattern': 'frequent_query_type',
                'data': {'query_type': most_common_type[0]},
                'confidence': most_common_type[1] / len(query_types)
            }
        
        return None
    
    def _apply_adaptations(self, user_id: str, patterns: List[Dict[str, Any]]) -> List[str]:
        """Aplica adaptações baseadas nos padrões."""
        adaptations = []
        
        for pattern in patterns:
            if pattern['confidence'] >= self.config['adaptation_threshold']:
                adaptation = self._create_adaptation(pattern)
                if adaptation:
                    adaptations.append(adaptation)
        
        return adaptations
    
    def _create_adaptation(self, pattern: Dict[str, Any]) -> Optional[str]:
        """Cria adaptação baseada no padrão."""
        if pattern['type'] == 'time_pattern':
            return f"Adaptação de horário: priorizar {pattern['data']['hour']}h"
        elif pattern['type'] == 'query_pattern':
            return f"Adaptação de consulta: otimizar para {pattern['data']['query_type']}"
        
        return None
    
    def _calculate_learning_confidence(self, user_id: str) -> float:
        """Calcula confiança do aprendizado."""
        profile = self.user_profiles.get(user_id, {})
        interactions_count = profile.get('interactions_count', 0)
        
        if interactions_count < self.config['min_interactions']:
            return 0.0
        
        # Confiança baseada no número de interações
        confidence = min(interactions_count / 20, 1.0)  # Máximo com 20 interações
        
        return confidence
    
    def _get_default_recommendations(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Gera recomendações padrão."""
        return [
            {
                'type': 'general',
                'title': 'Consulta de faturamento',
                'description': 'Verificar notas fiscais recentes',
                'priority': 0.8
            },
            {
                'type': 'general',
                'title': 'Status de entregas',
                'description': 'Consultar entregas pendentes',
                'priority': 0.7
            }
        ]
    
    def _generate_preference_recommendations(self, preference_type: str, preference_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Gera recomendações baseadas em preferências."""
        recommendations = []
        
        if preference_type == 'query_types':
            # Recomendar consultas do tipo mais usado
            most_used = max(preference_data.items(), key=lambda x: x[1])
            recommendations.append({
                'type': 'preference',
                'title': f'Consulta {most_used[0]}',
                'description': f'Baseado no seu uso frequente',
                'priority': 0.9
            })
        
        return recommendations
    
    def _generate_pattern_recommendations(self, pattern: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Gera recomendações baseadas em padrões."""
        recommendations = []
        
        if pattern['type'] == 'time_pattern':
            recommendations.append({
                'type': 'pattern',
                'title': 'Lembrete personalizado',
                'description': f'Consulta sugerida para {pattern["data"]["hour"]}h',
                'priority': pattern['confidence']
            })
        
        return recommendations
    
    def _rank_recommendations(self, recommendations: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ordena recomendações por relevância."""
        return sorted(recommendations, key=lambda x: x.get('priority', 0), reverse=True)
    
    def _adapt_detail_level(self, response: Dict[str, Any], detail_preference: str) -> Dict[str, Any]:
        """Adapta nível de detalhe da resposta."""
        if detail_preference == 'high':
            response['detail_level'] = 'high'
            response['adaptations_applied'].append('increased_detail')
        elif detail_preference == 'low':
            response['detail_level'] = 'low'
            response['adaptations_applied'].append('decreased_detail')
        
        return response
    
    def _adapt_presentation_format(self, response: Dict[str, Any], format_preference: str) -> Dict[str, Any]:
        """Adapta formato de apresentação."""
        response['presentation_format'] = format_preference
        response['adaptations_applied'].append(f'format_{format_preference}')
        return response
    
    def _adapt_language_style(self, response: Dict[str, Any], style_preference: str) -> Dict[str, Any]:
        """Adapta estilo de linguagem."""
        response['language_style'] = style_preference
        response['adaptations_applied'].append(f'language_{style_preference}')
        return response
    
    def _handle_negative_feedback(self, user_id: str, feedback: Dict[str, Any], profile: Dict[str, Any]) -> List[str]:
        """Lida com feedback negativo."""
        adjustments = []
        
        # Ajustar preferências baseado no feedback
        if 'too_detailed' in feedback.get('text', ''):
            profile.setdefault('preferences', {})['detail_level'] = 'low'
            adjustments.append('reduced_detail_preference')
        
        if 'too_simple' in feedback.get('text', ''):
            profile.setdefault('preferences', {})['detail_level'] = 'high'
            adjustments.append('increased_detail_preference')
        
        return adjustments
    
    def _handle_positive_feedback(self, user_id: str, feedback: Dict[str, Any], profile: Dict[str, Any]) -> List[str]:
        """Lida com feedback positivo."""
        adjustments = []
        
        # Reforçar preferências atuais
        if 'perfect_detail' in feedback.get('text', ''):
            current_detail = profile.get('preferences', {}).get('detail_level', 'medium')
            adjustments.append(f'reinforced_{current_detail}_detail')
        
        return adjustments


def get_adaptive_learning() -> AdaptiveLearning:
    """
    Obtém instância do sistema de aprendizado adaptativo.
    
    Returns:
        Instância do AdaptiveLearning
    """
    return AdaptiveLearning() 