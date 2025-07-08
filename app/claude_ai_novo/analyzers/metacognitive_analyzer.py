#!/usr/bin/env python3
"""
🧠 SISTEMA DE IA METACOGNITIVA
Auto-reflexão e melhoria contínua da performance do sistema
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MetacognitiveAnalyzer:
    """Sistema de IA Metacognitiva - Auto-reflexão e melhoria contínua"""
    
    def __init__(self):
        self.self_performance_history = []
        self.confidence_calibration = {}
        self.error_patterns = {}
        
    def analyze_own_performance(self, query: str, response: str, 
                              user_feedback: Optional[str] = None) -> Dict[str, Any]:
        """Analisa própria performance e identifica pontos de melhoria"""
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'query_complexity': self._assess_query_complexity(query),
            'response_quality': self._assess_response_quality(response),
            'confidence_score': self._calculate_confidence(query, response),
            'potential_improvements': [],
            'cognitive_load': self._assess_cognitive_load(query),
            'domain_coverage': self._assess_domain_coverage(query, response)
        }
        
        # Auto-crítica baseada em padrões conhecidos
        if user_feedback:
            analysis['user_satisfaction'] = self._interpret_user_feedback(user_feedback)
            analysis['calibration_error'] = abs(analysis['confidence_score'] - analysis['user_satisfaction'])
        
        # Identificar melhorias específicas
        analysis['potential_improvements'] = self._suggest_self_improvements(analysis)
        
        # Armazenar para análise de trends
        self.self_performance_history.append(analysis)
        
        return analysis
    
    def _assess_query_complexity(self, query: str) -> float:
        """Avalia complexidade da consulta (0-1)"""
        
        complexity_factors = [
            len(query.split()) > 10,  # Consulta longa
            any(word in query.lower() for word in ['e', 'ou', 'mas', 'porém']),  # Conjunções
            any(char in query for char in ['?', '!', ':']),  # Punctuation complexa
            len([w for w in query.split() if w.isupper()]) > 1,  # Múltiplas palavras maiúsculas
            'relatório' in query.lower() or 'excel' in query.lower(),  # Requer processamento
        ]
        
        return sum(complexity_factors) / len(complexity_factors)
    
    def _assess_response_quality(self, response: str) -> float:
        """Avalia qualidade da própria resposta (0-1)"""
        
        quality_factors = [
            len(response) > 100,  # Resposta substancial
            'dados' in response.lower(),  # Baseada em dados
            any(word in response.lower() for word in ['análise', 'resultado', 'encontrado']),
            not any(word in response.lower() for word in ['erro', 'não consegui', 'desculpe']),
            response.count('\n') > 2,  # Bem estruturada
            '**' in response or '*' in response,  # Formatação
        ]
        
        return sum(quality_factors) / len(quality_factors)
    
    def _calculate_confidence(self, query: str, response: str) -> float:
        """Calcula confiança na própria resposta"""
        
        confidence_factors = [
            self._assess_query_complexity(query) < 0.7,  # Consulta não muito complexa
            self._assess_response_quality(response) > 0.6,  # Resposta de boa qualidade
            'dados reais' in response.lower(),  # Baseada em dados reais
            len(response) > 200,  # Resposta detalhada
            not ('aproximadamente' in response.lower() or 'cerca de' in response.lower())  # Precisa
        ]
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _assess_cognitive_load(self, query: str) -> str:
        """Avalia carga cognitiva necessária para processar a consulta"""
        
        complexity = self._assess_query_complexity(query)
        
        if complexity > 0.8:
            return "HIGH"
        elif complexity > 0.5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _assess_domain_coverage(self, query: str, response: str) -> Dict[str, Any]:
        """Avalia cobertura de domínios na resposta"""
        
        domains = {
            'entregas': ['entrega', 'transportadora', 'agendamento', 'prazo'],
            'fretes': ['frete', 'valor', 'custo', 'aprovação'],
            'pedidos': ['pedido', 'cotação', 'separação', 'cliente'],
            'financeiro': ['pagamento', 'pendência', 'valor', 'despesa']
        }
        
        coverage = {}
        query_lower = query.lower()
        response_lower = response.lower()
        
        for domain, keywords in domains.items():
            query_matches = sum(1 for kw in keywords if kw in query_lower)
            response_matches = sum(1 for kw in keywords if kw in response_lower)
            
            if query_matches > 0:
                coverage[domain] = {
                    'requested': query_matches,
                    'covered': response_matches,
                    'coverage_ratio': response_matches / query_matches if query_matches > 0 else 0
                }
        
        return coverage
    
    def _interpret_user_feedback(self, user_feedback: str) -> float:
        """Interpreta feedback do usuário e converte para score de satisfação"""
        
        feedback_lower = user_feedback.lower().strip()
        
        # Palavras positivas
        positive_indicators = [
            'excelente', 'ótimo', 'perfeito', 'correto', 'bom', 'certo', 
            'satisfeito', 'útil', 'preciso', 'completo', 'obrigado'
        ]
        
        # Palavras negativas  
        negative_indicators = [
            'errado', 'incorreto', 'não', 'ruim', 'péssimo', 'erro',
            'problema', 'falhou', 'não encontrou', 'inútil', 'confuso'
        ]
        
        # Palavras de melhoria
        improvement_indicators = [
            'melhorar', 'poderia', 'faltou', 'incompleto', 'mais', 
            'detalhes', 'específico', 'expandir'
        ]
        
        # Calcular score baseado nas palavras encontradas
        positive_count = sum(1 for word in positive_indicators if word in feedback_lower)
        negative_count = sum(1 for word in negative_indicators if word in feedback_lower)
        improvement_count = sum(1 for word in improvement_indicators if word in feedback_lower)
        
        # Score base
        if positive_count > negative_count:
            base_score = 0.8
        elif negative_count > positive_count:
            base_score = 0.2
        elif improvement_count > 0:
            base_score = 0.6
        else:
            base_score = 0.5  # Neutro
        
        # Ajustar baseado na proporção
        total_indicators = positive_count + negative_count + improvement_count
        if total_indicators > 0:
            satisfaction = (positive_count * 1.0 + improvement_count * 0.6 + negative_count * 0.1) / total_indicators
        else:
            satisfaction = base_score
        
        return min(max(satisfaction, 0.0), 1.0)  # Garantir entre 0-1
    
    def _suggest_self_improvements(self, analysis: Dict[str, Any]) -> List[str]:
        """Sugere melhorias baseadas na auto-análise"""
        
        improvements = []
        
        if analysis['confidence_score'] < 0.6:
            improvements.append("Melhorar coleta de dados para aumentar confiança")
        
        if analysis['response_quality'] < 0.7:
            improvements.append("Aprimorar estruturação e formatação da resposta")
        
        if analysis['cognitive_load'] == "HIGH" and analysis['response_quality'] < 0.8:
            improvements.append("Desenvolver estratégias para consultas complexas")
        
        # Análise de cobertura de domínio
        for domain, coverage in analysis['domain_coverage'].items():
            if coverage['coverage_ratio'] < 0.8:
                improvements.append(f"Melhorar cobertura do domínio {domain}")
        
        return improvements

# Função de conveniência para criar instância
def get_metacognitive_analyzer() -> MetacognitiveAnalyzer:
    """Retorna instância do analisador metacognitivo"""
    return MetacognitiveAnalyzer() 