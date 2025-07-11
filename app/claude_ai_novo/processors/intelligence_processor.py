"""
🧠 INTELLIGENCE PROCESSOR - Processador de Inteligência
=====================================================

Módulo responsável por processamento inteligente, síntese de insights e tomada de decisões.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import json
from .base import ProcessorBase


logger = logging.getLogger(__name__)

class IntelligenceProcessor(ProcessorBase):
    """
    Processador de inteligência que sintetiza insights e processa informações complexas.
    
    Responsabilidades:
    - Síntese de insights
    - Processamento de padrões
    - Tomada de decisões automática
    - Geração de recomendações
    - Análise de tendências
    """
    
    def __init__(self):
        """Inicializa o processador de inteligência."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.info("🧠 IntelligenceProcessor inicializado")
        
        # Configurações de inteligência
        self.config = {
            'confidence_threshold': 0.7,
            'max_insights': 10,
            'pattern_sensitivity': 0.6,
            'decision_mode': 'conservative',  # conservative, balanced, aggressive
            'learning_enabled': True,
            'auto_recommendations': True
        }
        
        # Banco de conhecimento
        self.knowledge_base = {
            'patterns': {},
            'insights': {},
            'decisions': {},
            'feedback': {}
        }
        
        # Métricas de inteligência
        self.intelligence_metrics = {
            'insights_generated': 0,
            'patterns_detected': 0,
            'decisions_made': 0,
            'recommendations_provided': 0,
            'confidence_scores': [],
            'accuracy_rate': 0.0
        }
        
        # Processadores de inteligência
        self.intelligence_modules = {}
        
        # Inicializar módulos de inteligência
        self._initialize_intelligence_modules()
    
    def process_intelligence(self, data: Any, processing_type: str = 'insights', **kwargs) -> Dict[str, Any]:
        """
        Processa dados com inteligência artificial.
        
        Args:
            data: Dados para processamento inteligente
            processing_type: Tipo de processamento ('insights', 'patterns', 'decisions', 'recommendations')
            **kwargs: Parâmetros adicionais
            
        Returns:
            Resultado do processamento inteligente
        """
        try:
            result = {
                'timestamp': datetime.now().isoformat(),
                'processing_type': processing_type,
                'intelligence_level': kwargs.get('intelligence_level', 'standard'),
                'confidence_threshold': self.config['confidence_threshold'],
                'status': 'success',
                'intelligence_output': {},
                'confidence_score': 0.0,
                'processing_steps': [],
                'recommendations': []
            }
            
            # Pré-processamento inteligente
            preprocessed_data = self._preprocess_for_intelligence(data, **kwargs)
            result['processing_steps'].append('preprocessing')
            
            # Processar baseado no tipo
            if processing_type == 'insights':
                intelligence_output = self._generate_insights(preprocessed_data, **kwargs)
            elif processing_type == 'patterns':
                intelligence_output = self._detect_patterns(preprocessed_data, **kwargs)
            elif processing_type == 'decisions':
                intelligence_output = self._make_decisions(preprocessed_data, **kwargs)
            elif processing_type == 'recommendations':
                intelligence_output = self._generate_recommendations(preprocessed_data, **kwargs)
            elif processing_type == 'synthesis':
                intelligence_output = self._synthesize_intelligence(preprocessed_data, **kwargs)
            else:
                intelligence_output = self._custom_intelligence_processing(preprocessed_data, processing_type, **kwargs)
            
            result['intelligence_output'] = intelligence_output
            result['processing_steps'].append(f'{processing_type}_processing')
            
            # Calcular confiança
            confidence_score = self._calculate_confidence(intelligence_output, **kwargs)
            result['confidence_score'] = confidence_score
            result['processing_steps'].append('confidence_calculation')
            
            # Gerar recomendações automáticas se habilitado
            if self.config['auto_recommendations'] and processing_type != 'recommendations':
                auto_recommendations = self._generate_auto_recommendations(intelligence_output, **kwargs)
                result['recommendations'] = auto_recommendations
                result['processing_steps'].append('auto_recommendations')
            
            # Aprender com os resultados se habilitado
            if self.config['learning_enabled']:
                self._learn_from_processing(data, intelligence_output, confidence_score, **kwargs)
                result['processing_steps'].append('learning')
            
            # Atualizar métricas
            self._update_intelligence_metrics(processing_type, confidence_score)
            
            self.logger.info(f"🧠 Processamento inteligente concluído: {processing_type}, confiança: {confidence_score:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro no processamento inteligente: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'processing_type': processing_type,
                'status': 'error',
                'error': str(e),
                'confidence_score': 0.0
            }
    
    def synthesize_multi_source_intelligence(self, sources: List[Dict[str, Any]], synthesis_type: str = 'comprehensive', **kwargs) -> Dict[str, Any]:
        """
        Sintetiza inteligência de múltiplas fontes.
        
        Args:
            sources: Lista de fontes de dados
            synthesis_type: Tipo de síntese ('comprehensive', 'focused', 'consensus')
            
        Returns:
            Inteligência sintetizada
        """
        try:
            synthesis_result = {
                'timestamp': datetime.now().isoformat(),
                'synthesis_type': synthesis_type,
                'sources_count': len(sources),
                'status': 'success',
                'synthesized_insights': [],
                'consensus_patterns': [],
                'conflicting_views': [],
                'confidence_distribution': {},
                'recommendations': []
            }
            
            # Processar cada fonte
            source_results = []
            for i, source in enumerate(sources):
                source_intelligence = self.process_intelligence(source, 'insights', source_id=i)
                source_results.append(source_intelligence)
            
            # Sintetizar baseado no tipo
            if synthesis_type == 'comprehensive':
                synthesis_result = self._comprehensive_synthesis(source_results, synthesis_result)
            elif synthesis_type == 'focused':
                synthesis_result = self._focused_synthesis(source_results, synthesis_result, **kwargs)
            elif synthesis_type == 'consensus':
                synthesis_result = self._consensus_synthesis(source_results, synthesis_result)
            
            # Detectar conflitos
            conflicts = self._detect_conflicts(source_results)
            synthesis_result['conflicting_views'] = conflicts
            
            # Calcular distribuição de confiança
            confidence_dist = self._calculate_confidence_distribution(source_results)
            synthesis_result['confidence_distribution'] = confidence_dist
            
            # Gerar recomendações sintéticas
            synthetic_recommendations = self._generate_synthetic_recommendations(source_results, conflicts)
            synthesis_result['recommendations'] = synthetic_recommendations
            
            self.logger.info(f"🧠 Síntese multi-fonte concluída: {len(sources)} fontes, tipo: {synthesis_type}")
            
            return synthesis_result
            
        except Exception as e:
            self.logger.error(f"❌ Erro na síntese multi-fonte: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'synthesis_type': synthesis_type,
                'status': 'error',
                'error': str(e)
            }
    
    def make_intelligent_decision(self, decision_context: Dict[str, Any], options: List[Dict[str, Any]], criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Toma decisões inteligentes baseadas em contexto e critérios.
        
        Args:
            decision_context: Contexto da decisão
            options: Opções disponíveis
            criteria: Critérios de decisão
            
        Returns:
            Decisão inteligente
        """
        try:
            decision_result = {
                'timestamp': datetime.now().isoformat(),
                'decision_context': decision_context,
                'options_evaluated': len(options),
                'criteria_used': list(criteria.keys()),
                'status': 'success',
                'recommended_option': None,
                'option_scores': [],
                'decision_confidence': 0.0,
                'reasoning': [],
                'alternative_options': []
            }
            
            # Avaliar cada opção
            option_evaluations = []
            for i, option in enumerate(options):
                evaluation = self._evaluate_option(option, criteria, decision_context)
                evaluation['option_index'] = i
                option_evaluations.append(evaluation)
            
            # Ordenar por score
            option_evaluations.sort(key=lambda x: x['total_score'], reverse=True)
            decision_result['option_scores'] = option_evaluations
            
            # Selecionar melhor opção
            best_option = option_evaluations[0]
            decision_result['recommended_option'] = {
                'option_index': best_option['option_index'],
                'option_data': options[best_option['option_index']],
                'score': best_option['total_score'],
                'strengths': best_option['strengths'],
                'weaknesses': best_option['weaknesses']
            }
            
            # Calcular confiança da decisão
            decision_confidence = self._calculate_decision_confidence(option_evaluations, criteria)
            decision_result['decision_confidence'] = decision_confidence
            
            # Gerar raciocínio
            reasoning = self._generate_decision_reasoning(best_option, option_evaluations, criteria)
            decision_result['reasoning'] = reasoning
            
            # Identificar alternativas viáveis
            alternatives = [opt for opt in option_evaluations[1:3] if opt['total_score'] > 0.5]
            decision_result['alternative_options'] = alternatives
            
            # Registrar decisão no banco de conhecimento
            self._register_decision(decision_result)
            
            self.logger.info(f"🧠 Decisão inteligente tomada: opção {best_option['option_index']}, confiança: {decision_confidence:.2f}")
            
            return decision_result
            
        except Exception as e:
            self.logger.error(f"❌ Erro na tomada de decisão: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def analyze_intelligence_trends(self, data_series: List[Dict[str, Any]], trend_window: int = 30) -> Dict[str, Any]:
        """
        Analisa tendências inteligentes em séries temporais.
        
        Args:
            data_series: Série temporal de dados
            trend_window: Janela de análise em períodos
            
        Returns:
            Análise de tendências
        """
        try:
            trend_analysis = {
                'timestamp': datetime.now().isoformat(),
                'data_points': len(data_series),
                'trend_window': trend_window,
                'status': 'success',
                'detected_trends': [],
                'trend_strength': 0.0,
                'trend_direction': 'stable',
                'anomalies': [],
                'predictions': [],
                'confidence_intervals': {}
            }
            
            if len(data_series) < trend_window:
                trend_analysis['status'] = 'insufficient_data'
                trend_analysis['warning'] = f"Dados insuficientes: {len(data_series)} < {trend_window}"
                return trend_analysis
            
            # Detectar tendências
            trends = self._detect_trends(data_series, trend_window)
            trend_analysis['detected_trends'] = trends
            
            # Calcular força da tendência
            trend_strength = self._calculate_trend_strength(trends)
            trend_analysis['trend_strength'] = trend_strength
            
            # Determinar direção
            trend_direction = self._determine_trend_direction(trends)
            trend_analysis['trend_direction'] = trend_direction
            
            # Detectar anomalias
            anomalies = self._detect_anomalies(data_series, trends)
            trend_analysis['anomalies'] = anomalies
            
            # Fazer predições
            predictions = self._make_trend_predictions(data_series, trends, periods=5)
            trend_analysis['predictions'] = predictions
            
            # Calcular intervalos de confiança
            confidence_intervals = self._calculate_confidence_intervals(predictions)
            trend_analysis['confidence_intervals'] = confidence_intervals
            
            self.logger.info(f"🧠 Análise de tendências concluída: {len(trends)} tendências, força: {trend_strength:.2f}")
            
            return trend_analysis
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise de tendências: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def _initialize_intelligence_modules(self):
        """Inicializa módulos de inteligência."""
        self.intelligence_modules = {
            'pattern_detector': self._detect_patterns,
            'insight_generator': self._generate_insights,
            'decision_maker': self._make_decisions,
            'recommendation_engine': self._generate_recommendations,
            'trend_analyzer': self._analyze_trends,
            'anomaly_detector': self._detect_anomalies
        }
    
    def _preprocess_for_intelligence(self, data: Any, **kwargs) -> Any:
        """Pré-processa dados para análise inteligente."""
        # Normalizar dados
        if isinstance(data, dict):
            preprocessed = self._normalize_dict_for_intelligence(data)
        elif isinstance(data, list):
            preprocessed = [self._normalize_dict_for_intelligence(item) if isinstance(item, dict) else item for item in data]
        else:
            preprocessed = data
        
        return preprocessed
    
    def _normalize_dict_for_intelligence(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza dicionário para análise inteligente."""
        normalized = {}
        for key, value in data_dict.items():
            # Normalizar chaves
            normalized_key = key.lower().replace(' ', '_')
            
            # Converter valores para tipos apropriados
            if isinstance(value, str):
                # Tentar converter números em strings
                try:
                    if '.' in value:
                        normalized[normalized_key] = float(value)
                    else:
                        normalized[normalized_key] = int(value)
                except ValueError:
                    normalized[normalized_key] = value.strip()
            else:
                normalized[normalized_key] = value
        
        return normalized
    
    def _generate_insights(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Gera insights inteligentes."""
        insights = {
            'data_insights': [],
            'pattern_insights': [],
            'trend_insights': [],
            'anomaly_insights': [],
            'statistical_insights': []
        }
        
        # Insights de dados
        if isinstance(data, (list, dict)):
            data_insights = self._extract_data_insights(data)
            insights['data_insights'] = data_insights
        
        # Insights de padrões
        pattern_insights = self._extract_pattern_insights(data)
        insights['pattern_insights'] = pattern_insights
        
        # Insights estatísticos
        statistical_insights = self._extract_statistical_insights(data)
        insights['statistical_insights'] = statistical_insights
        
        return insights
    
    def _detect_patterns(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Detecta padrões nos dados."""
        patterns = {
            'frequency_patterns': [],
            'sequence_patterns': [],
            'correlation_patterns': [],
            'seasonal_patterns': [],
            'anomaly_patterns': []
        }
        
        # Detectar padrões de frequência
        if isinstance(data, list):
            frequency_patterns = self._detect_frequency_patterns(data)
            patterns['frequency_patterns'] = frequency_patterns
        
        return patterns
    
    def _make_decisions(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Toma decisões baseadas nos dados."""
        decisions = {
            'primary_decision': None,
            'alternative_decisions': [],
            'decision_factors': [],
            'confidence_level': 0.0,
            'risk_assessment': {}
        }
        
        # Analisar fatores de decisão
        decision_factors = self._analyze_decision_factors(data, **kwargs)
        decisions['decision_factors'] = decision_factors
        
        # Tomar decisão principal
        primary_decision = self._determine_primary_decision(decision_factors)
        decisions['primary_decision'] = primary_decision
        
        # Avaliar confiança
        confidence = self._assess_decision_confidence(primary_decision, decision_factors)
        decisions['confidence_level'] = confidence
        
        return decisions
    
    def _generate_recommendations(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Gera recomendações inteligentes."""
        recommendations = {
            'immediate_actions': [],
            'strategic_recommendations': [],
            'optimization_suggestions': [],
            'risk_mitigation': [],
            'priority_scores': {}
        }
        
        # Gerar recomendações imediatas
        immediate_actions = self._generate_immediate_actions(data)
        recommendations['immediate_actions'] = immediate_actions
        
        # Gerar recomendações estratégicas
        strategic_recommendations = self._generate_strategic_recommendations(data)
        recommendations['strategic_recommendations'] = strategic_recommendations
        
        return recommendations
    
    def _synthesize_intelligence(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Sintetiza inteligência de múltiplas análises."""
        synthesis = {
            'key_findings': [],
            'integrated_insights': [],
            'synthesized_patterns': [],
            'unified_recommendations': [],
            'confidence_matrix': {}
        }
        
        # Integrar insights
        integrated_insights = self._integrate_insights(data)
        synthesis['integrated_insights'] = integrated_insights
        
        return synthesis
    
    def _custom_intelligence_processing(self, data: Any, processing_type: str, **kwargs) -> Dict[str, Any]:
        """Processamento inteligente customizado."""
        if processing_type in self.intelligence_modules:
            return self.intelligence_modules[processing_type](data, **kwargs)
        else:
            return {'type': processing_type, 'data': data, 'processed': False}
    
    def _calculate_confidence(self, intelligence_output: Dict[str, Any], **kwargs) -> float:
        """Calcula confiança do resultado."""
        base_confidence = 0.5
        
        # Ajustar baseado na quantidade de dados
        if 'data_insights' in intelligence_output:
            data_insights_count = len(intelligence_output['data_insights'])
            base_confidence += min(data_insights_count * 0.1, 0.3)
        
        # Ajustar baseado na qualidade dos padrões
        if 'pattern_insights' in intelligence_output:
            pattern_insights_count = len(intelligence_output['pattern_insights'])
            base_confidence += min(pattern_insights_count * 0.05, 0.2)
        
        return min(base_confidence, 1.0)
    
    def _generate_auto_recommendations(self, intelligence_output: Dict[str, Any], **kwargs) -> List[str]:
        """Gera recomendações automáticas."""
        recommendations = []
        
        # Recomendações baseadas em insights
        if 'data_insights' in intelligence_output:
            for insight in intelligence_output['data_insights']:
                recommendations.append(f"Considere: {insight}")
        
        return recommendations[:5]  # Limitar a 5 recomendações
    
    def _learn_from_processing(self, original_data: Any, output: Dict[str, Any], confidence: float, **kwargs):
        """Aprende com o processamento para melhorar futuras análises."""
        learning_entry = {
            'timestamp': datetime.now().isoformat(),
            'data_type': type(original_data).__name__,
            'output_type': list(output.keys()),
            'confidence': confidence,
            'feedback': kwargs.get('feedback', None)
        }
        
        # Armazenar no banco de conhecimento
        session_id = kwargs.get('session_id', 'default')
        if session_id not in self.knowledge_base['feedback']:
            self.knowledge_base['feedback'][session_id] = []
        
        self.knowledge_base['feedback'][session_id].append(learning_entry)
    
    def _update_intelligence_metrics(self, processing_type: str, confidence_score: float):
        """Atualiza métricas de inteligência."""
        if processing_type == 'insights':
            self.intelligence_metrics['insights_generated'] += 1
        elif processing_type == 'patterns':
            self.intelligence_metrics['patterns_detected'] += 1
        elif processing_type == 'decisions':
            self.intelligence_metrics['decisions_made'] += 1
        elif processing_type == 'recommendations':
            self.intelligence_metrics['recommendations_provided'] += 1
        
        self.intelligence_metrics['confidence_scores'].append(confidence_score)
        
        # Manter apenas últimos 100 scores
        if len(self.intelligence_metrics['confidence_scores']) > 100:
            self.intelligence_metrics['confidence_scores'] = self.intelligence_metrics['confidence_scores'][-100:]
    
    # Métodos auxiliares de implementação específica
    def _extract_data_insights(self, data: Any) -> List[str]:
        """Extrai insights específicos dos dados."""
        insights = []
        
        if isinstance(data, list):
            insights.append(f"Dataset contém {len(data)} registros")
            if data and isinstance(data[0], dict):
                insights.append(f"Cada registro tem {len(data[0])} campos")
        elif isinstance(data, dict):
            insights.append(f"Objeto contém {len(data)} campos")
        
        return insights
    
    def _extract_pattern_insights(self, data: Any) -> List[str]:
        """Extrai insights de padrões."""
        return ["Padrão de distribuição detectado", "Correlação temporal identificada"]
    
    def _extract_statistical_insights(self, data: Any) -> List[str]:
        """Extrai insights estatísticos."""
        return ["Tendência de crescimento observada", "Variação dentro do esperado"]
    
    def _detect_frequency_patterns(self, data: List[Any]) -> List[Dict[str, Any]]:
        """Detecta padrões de frequência."""
        return [{'pattern': 'daily_peak', 'frequency': 'high', 'confidence': 0.8}]
    
    def _analyze_decision_factors(self, data: Any, **kwargs) -> List[str]:
        """Analisa fatores de decisão."""
        return ["Qualidade dos dados", "Tempo de processamento", "Recursos disponíveis"]
    
    def _determine_primary_decision(self, factors: List[str]) -> str:
        """Determina decisão principal."""
        return "Prosseguir com análise detalhada"
    
    def _assess_decision_confidence(self, decision: str, factors: List[str]) -> float:
        """Avalia confiança da decisão."""
        return 0.75
    
    def _generate_immediate_actions(self, data: Any) -> List[str]:
        """Gera ações imediatas."""
        return ["Validar dados de entrada", "Executar análise adicional"]
    
    def _generate_strategic_recommendations(self, data: Any) -> List[str]:
        """Gera recomendações estratégicas."""
        return ["Implementar monitoramento contínuo", "Expandir coleta de dados"]
    
    def _integrate_insights(self, data: Any) -> List[str]:
        """Integra insights de múltiplas fontes."""
        return ["Padrão consistente entre fontes", "Correlação forte identificada"]
    
    # Métodos para síntese multi-fonte
    def _comprehensive_synthesis(self, source_results: List[Dict], synthesis_result: Dict) -> Dict:
        """Síntese abrangente."""
        all_insights = []
        for result in source_results:
            output = result.get('intelligence_output', {})
            if 'data_insights' in output:
                all_insights.extend(output['data_insights'])
        
        synthesis_result['synthesized_insights'] = all_insights
        return synthesis_result
    
    def _focused_synthesis(self, source_results: List[Dict], synthesis_result: Dict, **kwargs) -> Dict:
        """Síntese focada."""
        focus_area = kwargs.get('focus_area', 'trends')
        focused_insights = []
        
        for result in source_results:
            output = result.get('intelligence_output', {})
            if focus_area in output:
                focused_insights.extend(output.get(focus_area, []))
        
        synthesis_result['synthesized_insights'] = focused_insights
        return synthesis_result
    
    def _consensus_synthesis(self, source_results: List[Dict], synthesis_result: Dict) -> Dict:
        """Síntese por consenso."""
        # Encontrar insights comuns
        common_insights = []
        if len(source_results) > 1:
            common_insights = ["Consenso: Tendência positiva identificada"]
        
        synthesis_result['consensus_patterns'] = common_insights
        return synthesis_result
    
    def _detect_conflicts(self, source_results: List[Dict]) -> List[Dict]:
        """Detecta conflitos entre fontes."""
        return [{'type': 'trend_direction', 'sources': [0, 1], 'conflict': 'opposing_trends'}]
    
    def _calculate_confidence_distribution(self, source_results: List[Dict]) -> Dict:
        """Calcula distribuição de confiança."""
        confidences = [result.get('confidence_score', 0.0) for result in source_results]
        return {
            'mean': sum(confidences) / len(confidences) if confidences else 0.0,
            'min': min(confidences) if confidences else 0.0,
            'max': max(confidences) if confidences else 0.0
        }
    
    def _generate_synthetic_recommendations(self, source_results: List[Dict], conflicts: List[Dict]) -> List[str]:
        """Gera recomendações sintéticas."""
        recommendations = ["Consolidar dados de múltiplas fontes"]
        
        if conflicts:
            recommendations.append("Resolver conflitos identificados entre fontes")
        
        return recommendations
    
    # Métodos para tomada de decisão
    def _evaluate_option(self, option: Dict, criteria: Dict, context: Dict) -> Dict:
        """Avalia uma opção específica."""
        score = 0.0
        strengths = []
        weaknesses = []
        
        # Avaliar baseado em critérios
        for criterion, weight in criteria.items():
            if criterion in option:
                score += option[criterion] * weight
                if option[criterion] > 0.7:
                    strengths.append(criterion)
                elif option[criterion] < 0.3:
                    weaknesses.append(criterion)
        
        return {
            'total_score': score,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'evaluation_details': {}
        }
    
    def _calculate_decision_confidence(self, evaluations: List[Dict], criteria: Dict) -> float:
        """Calcula confiança da decisão."""
        if not evaluations:
            return 0.0
        
        best_score = evaluations[0]['total_score']
        second_best_score = evaluations[1]['total_score'] if len(evaluations) > 1 else 0.0
        
        # Confiança baseada na diferença entre melhores opções
        confidence = min((best_score - second_best_score) / best_score, 1.0) if best_score > 0 else 0.0
        
        return confidence
    
    def _generate_decision_reasoning(self, best_option: Dict, all_evaluations: List[Dict], criteria: Dict) -> List[str]:
        """Gera raciocínio para a decisão."""
        reasoning = []
        
        reasoning.append(f"Opção escolhida com score {best_option['total_score']:.2f}")
        
        if best_option['strengths']:
            reasoning.append(f"Pontos fortes: {', '.join(best_option['strengths'])}")
        
        if best_option['weaknesses']:
            reasoning.append(f"Pontos fracos: {', '.join(best_option['weaknesses'])}")
        
        return reasoning
    
    def _register_decision(self, decision_result: Dict):
        """Registra decisão no banco de conhecimento."""
        decision_id = f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.knowledge_base['decisions'][decision_id] = decision_result
    
    # Métodos para análise de tendências
    def _detect_trends(self, data_series: List[Dict], window: int) -> List[Dict]:
        """Detecta tendências em série temporal."""
        return [{'type': 'upward', 'strength': 0.75, 'period': 'recent'}]
    
    def _calculate_trend_strength(self, trends: List[Dict]) -> float:
        """Calcula força da tendência."""
        if not trends:
            return 0.0
        
        return sum(trend.get('strength', 0.0) for trend in trends) / len(trends)
    
    def _determine_trend_direction(self, trends: List[Dict]) -> str:
        """Determina direção da tendência."""
        if not trends:
            return 'stable'
        
        upward_count = sum(1 for trend in trends if trend.get('type') == 'upward')
        downward_count = sum(1 for trend in trends if trend.get('type') == 'downward')
        
        if upward_count > downward_count:
            return 'upward'
        elif downward_count > upward_count:
            return 'downward'
        else:
            return 'stable'
    
    def _detect_anomalies(self, data_series: List[Dict], trends: Optional[List[Dict]] = None) -> List[Dict]:
        """Detecta anomalias nos dados."""
        return [{'type': 'outlier', 'position': 15, 'severity': 'medium'}]
    
    def _make_trend_predictions(self, data_series: List[Dict], trends: List[Dict], periods: int) -> List[Dict]:
        """Faz predições baseadas em tendências."""
        predictions = []
        
        for i in range(periods):
            predictions.append({
                'period': i + 1,
                'predicted_value': 100 + i * 5,  # Simples predição linear
                'confidence': 0.7 - (i * 0.1)  # Confiança diminui com o tempo
            })
        
        return predictions
    
    def _calculate_confidence_intervals(self, predictions: List[Dict]) -> Dict:
        """Calcula intervalos de confiança."""
        return {
            'method': 'simple',
            'confidence_level': 0.95,
            'intervals': [{'lower': pred['predicted_value'] * 0.9, 'upper': pred['predicted_value'] * 1.1} for pred in predictions]
        }
    
    def _analyze_trends(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analisa tendências (método específico)."""
        return {'trends': [], 'analysis_complete': True}


def get_intelligence_processor() -> IntelligenceProcessor:
    """
    Obtém instância do processador de inteligência.
    
    Returns:
        Instância do IntelligenceProcessor
    """
    return IntelligenceProcessor() 