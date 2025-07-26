#!/usr/bin/env python3
"""
🧠 HUMAN-IN-THE-LOOP LEARNING SYSTEM
Sistema de aprendizado contínuo baseado em feedback humano expert
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
from dataclasses import dataclass
try:
    from flask_login import current_user
    FLASK_LOGIN_AVAILABLE = True
except ImportError:
    from unittest.mock import Mock
    current_user = Mock()
    FLASK_LOGIN_AVAILABLE = False
try:
    from flask import current_app
    FLASK_AVAILABLE = True
except ImportError:
    current_app = None
    FLASK_AVAILABLE = False
from app.claude_ai_novo.utils.flask_fallback import get_db


logger = logging.getLogger(__name__)

class FeedbackType(Enum):

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Tipos de feedback do usuário"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    CORRECTION = "correction"
    IMPROVEMENT = "improvement"
    BUG_REPORT = "bug_report"

class FeedbackSeverity(Enum):
    """Severidade do feedback para priorização"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class UserFeedback:
    """Estrutura para feedback do usuário"""
    feedback_id: str
    user_id: str
    query_original: str
    response_original: str
    feedback_type: FeedbackType
    severity: FeedbackSeverity
    feedback_text: str
    suggested_improvement: Optional[str]
    timestamp: datetime
    context: Dict[str, Any]
    processed: bool = False
    applied: bool = False

@dataclass
class LearningPattern:
    """Padrão de aprendizado identificado"""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    confidence_score: float
    improvement_suggestion: str
    examples: List[str]
    created_at: datetime

class HumanInLoopLearning:
    """Sistema de aprendizado com humano no loop"""
    
    def __init__(self):
        self.feedback_storage = []
        self.learning_patterns = []
        self.user_preferences = {}
        self.improvement_queue = []
        
    def capture_feedback(self, query: str, response: str, user_feedback: str, 
                        feedback_type: str, severity: str = "medium", 
                        context: Optional[Dict[str, Any]] = None) -> str:
        """Captura feedback do usuário sobre uma resposta"""
        
        try:
            # Gerar ID único para o feedback
            feedback_id = f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.feedback_storage)}"
            
            # Criar objeto de feedback
            feedback = UserFeedback(
                feedback_id=feedback_id,
                user_id=str(getattr(current_user, 'id', 'anonymous')),
                query_original=query,
                response_original=response,
                feedback_type=FeedbackType(feedback_type),
                severity=FeedbackSeverity(severity),
                feedback_text=user_feedback,
                suggested_improvement=context.get('suggested_improvement') if context else None,
                timestamp=datetime.now(),
                context=context or {},
                processed=False,
                applied=False
            )
            
            # Armazenar feedback
            self.feedback_storage.append(feedback)
            
            # Processar feedback imediatamente se crítico
            if feedback.severity == FeedbackSeverity.CRITICAL:
                self._process_critical_feedback(feedback)
            
            # Analisar padrões
            self._analyze_feedback_patterns()
            
            logger.info(f"💡 Feedback capturado: {feedback_id} - {feedback_type}")
            
            return feedback_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao capturar feedback: {e}")
            return f"Erro: {str(e)}"
    
    def _process_critical_feedback(self, feedback: UserFeedback):
        """Processa feedback crítico imediatamente"""
        
        logger.warning(f"🚨 FEEDBACK CRÍTICO: {feedback.feedback_id}")
        
        # Adicionar à fila de melhorias prioritárias
        improvement = {
            'priority': 'CRITICAL',
            'feedback_id': feedback.feedback_id,
            'issue': feedback.feedback_text,
            'suggested_fix': feedback.suggested_improvement,
            'timestamp': feedback.timestamp.isoformat(),
            'context': feedback.context
        }
        
        self.improvement_queue.insert(0, improvement)  # Inserir no início
        
        # Log para admin
        logger.critical(f"Feedback crítico requer atenção: {feedback.feedback_text}")
    
    def _analyze_feedback_patterns(self):
        """Analisa padrões nos feedbacks para identificar melhorias sistemáticas"""
        
        if len(self.feedback_storage) < 5:
            return  # Necessário mais dados
        
        # Analisar últimos 30 feedbacks
        recent_feedbacks = self.feedback_storage[-30:]
        
        # Padrão 1: Erros de interpretação de cliente
        client_errors = [f for f in recent_feedbacks 
                        if 'cliente' in f.feedback_text.lower() and 
                        f.feedback_type in [FeedbackType.NEGATIVE, FeedbackType.CORRECTION]]
        
        if len(client_errors) >= 3:
            self._create_learning_pattern(
                pattern_type="client_interpretation_error",
                description="Sistema confunde clientes frequentemente",
                frequency=len(client_errors),
                examples=[f.feedback_text for f in client_errors[-3:]],
                improvement="Melhorar detecção semântica de clientes"
            )
        
        # Padrão 2: Dados incorretos ou ausentes
        data_errors = [f for f in recent_feedbacks 
                      if any(word in f.feedback_text.lower() 
                            for word in ['dados incorretos', 'não encontrou', 'erro nos dados'])]
        
        if len(data_errors) >= 2:
            self._create_learning_pattern(
                pattern_type="data_accuracy_issue",
                description="Problemas recorrentes com precisão de dados",
                frequency=len(data_errors),
                examples=[f.feedback_text for f in data_errors],
                improvement="Revisar queries e validação de dados"
            )
        
        # Padrão 3: Problemas de formatação ou apresentação
        format_issues = [f for f in recent_feedbacks 
                        if any(word in f.feedback_text.lower() 
                              for word in ['formato', 'apresentação', 'layout', 'difícil de ler'])]
        
        if len(format_issues) >= 2:
            self._create_learning_pattern(
                pattern_type="presentation_issue",
                description="Problemas com formatação ou apresentação",
                frequency=len(format_issues),
                examples=[f.feedback_text for f in format_issues],
                improvement="Melhorar templates de resposta e formatação"
            )
    
    def _create_learning_pattern(self, pattern_type: str, description: str, 
                               frequency: int, examples: List[str], improvement: str):
        """Cria um novo padrão de aprendizado"""
        
        pattern_id = f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pattern_type}"
        
        # Verificar se padrão similar já existe
        existing_pattern = next((p for p in self.learning_patterns 
                               if p.pattern_type == pattern_type), None)
        
        if existing_pattern:
            # Atualizar padrão existente
            existing_pattern.frequency += frequency
            existing_pattern.examples.extend(examples[-2:])  # Adicionar exemplos mais recentes
            existing_pattern.confidence_score = min(existing_pattern.confidence_score + 0.1, 1.0)
            logger.info(f"📈 Padrão atualizado: {pattern_type} (freq: {existing_pattern.frequency})")
        else:
            # Criar novo padrão
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=description,
                frequency=frequency,
                confidence_score=min(frequency * 0.2, 1.0),
                improvement_suggestion=improvement,
                examples=examples,
                created_at=datetime.now()
            )
            
            self.learning_patterns.append(pattern)
            logger.info(f"🆕 Novo padrão identificado: {pattern_type}")
            
            # Adicionar à fila de melhorias se confiança alta
            if pattern.confidence_score > 0.6:
                self._add_to_improvement_queue(pattern)
    
    def _add_to_improvement_queue(self, pattern: LearningPattern):
        """Adiciona padrão à fila de melhorias"""
        
        improvement = {
            'priority': 'HIGH' if pattern.confidence_score > 0.8 else 'MEDIUM',
            'pattern_id': pattern.pattern_id,
            'type': 'pattern_improvement',
            'description': pattern.description,
            'suggested_fix': pattern.improvement_suggestion,
            'confidence': pattern.confidence_score,
            'frequency': pattern.frequency,
            'examples': pattern.examples,
            'timestamp': datetime.now().isoformat()
        }
        
        self.improvement_queue.append(improvement)
        logger.info(f"➕ Melhoria adicionada à fila: {pattern.pattern_type}")
    
    def get_improvement_suggestions(self, priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna sugestões de melhoria baseadas no aprendizado"""
        
        if priority_filter:
            filtered_queue = [item for item in self.improvement_queue 
                            if item['priority'] == priority_filter.upper()]
        else:
            filtered_queue = self.improvement_queue
        
        # Ordenar por prioridade e timestamp
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        filtered_queue.sort(key=lambda x: (priority_order.get(x['priority'], 4), x['timestamp']))
        
        return filtered_queue
    
    def apply_improvement(self, improvement_id: str, implemented: bool = True, 
                         notes: str = "") -> bool:
        """Marca uma melhoria como implementada"""
        
        # Encontrar melhoria na fila
        improvement = next((item for item in self.improvement_queue 
                          if item.get('pattern_id') == improvement_id or 
                          item.get('feedback_id') == improvement_id), None)
        
        if not improvement:
            return False
        
        # Marcar como implementada
        improvement['implemented'] = implemented
        improvement['implementation_date'] = datetime.now().isoformat()
        improvement['implementation_notes'] = notes
        
        # Se relacionado a feedback, marcar feedback como aplicado
        if 'feedback_id' in improvement:
            feedback = next((f for f in self.feedback_storage 
                           if f.feedback_id == improvement['feedback_id']), None)
            if feedback:
                feedback.applied = implemented
        
        logger.info(f"✅ Melhoria aplicada: {improvement_id}")
        return True
    
    def generate_learning_report(self, days: int = 30) -> Dict[str, Any]:
        """Gera relatório de aprendizado dos últimos N dias"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filtrar feedbacks recentes
        recent_feedbacks = [f for f in self.feedback_storage if f.timestamp >= cutoff_date]
        
        if not recent_feedbacks:
            return {"message": f"Nenhum feedback nos últimos {days} dias"}
        
        # Estatísticas de feedback
        feedback_stats = {
            'total': len(recent_feedbacks),
            'by_type': {},
            'by_severity': {},
            'by_user': {}
        }
        
        for feedback in recent_feedbacks:
            # Por tipo
            fb_type = feedback.feedback_type.value
            feedback_stats['by_type'][fb_type] = feedback_stats['by_type'].get(fb_type, 0) + 1
            
            # Por severidade
            severity = feedback.severity.value
            feedback_stats['by_severity'][severity] = feedback_stats['by_severity'].get(severity, 0) + 1
            
            # Por usuário
            user = feedback.user_id
            feedback_stats['by_user'][user] = feedback_stats['by_user'].get(user, 0) + 1
        
        # Padrões identificados
        recent_patterns = [p for p in self.learning_patterns if p.created_at >= cutoff_date]
        
        # Melhorias sugeridas
        improvement_stats = {
            'total_suggestions': len(self.improvement_queue),
            'by_priority': {},
            'implemented': len([i for i in self.improvement_queue if i.get('implemented', False)])
        }
        
        for improvement in self.improvement_queue:
            priority = improvement['priority']
            improvement_stats['by_priority'][priority] = improvement_stats['by_priority'].get(priority, 0) + 1
        
        # Trends e insights
        trends = self._analyze_trends(recent_feedbacks)
        
        return {
            'period': f"Últimos {days} dias",
            'feedback_statistics': feedback_stats,
            'patterns_identified': len(recent_patterns),
            'patterns_details': [
                {
                    'type': p.pattern_type,
                    'description': p.description,
                    'frequency': p.frequency,
                    'confidence': p.confidence_score
                } for p in recent_patterns
            ],
            'improvement_statistics': improvement_stats,
            'trends_and_insights': trends,
            'top_improvement_suggestions': self.get_improvement_suggestions()[:5]
        }
    
    def _analyze_trends(self, feedbacks: List[UserFeedback]) -> Dict[str, Any]:
        """Analisa trends nos feedbacks"""
        
        if len(feedbacks) < 5:
            return {"message": "Dados insuficientes para análise de trends"}
        
        # Analisar evolução temporal
        weekly_feedback = {}
        for feedback in feedbacks:
            week = feedback.timestamp.strftime('%Y-W%U')
            weekly_feedback[week] = weekly_feedback.get(week, 0) + 1
        
        # Calcular trend
        weeks = sorted(weekly_feedback.keys())
        if len(weeks) >= 2:
            recent_avg = sum(weekly_feedback[w] for w in weeks[-2:]) / 2
            older_avg = sum(weekly_feedback[w] for w in weeks[:-2]) / max(len(weeks) - 2, 1)
            trend = "increasing" if recent_avg > older_avg else "decreasing"
        else:
            trend = "stable"
        
        # Identificar problemas recorrentes
        common_issues = {}
        for feedback in feedbacks:
            words = feedback.feedback_text.lower().split()
            for word in words:
                if len(word) > 4:  # Palavras significativas
                    common_issues[word] = common_issues.get(word, 0) + 1
        
        # Top 5 palavras mais mencionadas
        top_issues = sorted(common_issues.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'feedback_trend': trend,
            'weekly_distribution': weekly_feedback,
            'most_mentioned_issues': top_issues,
            'satisfaction_indicator': self._calculate_satisfaction_score(feedbacks)
        }
    
    def _calculate_satisfaction_score(self, feedbacks: List[UserFeedback]) -> float:
        """Calcula score de satisfação baseado nos feedbacks"""
        
        if not feedbacks:
            return 0.5  # Neutro
        
        # Pesos por tipo de feedback
        weights = {
            FeedbackType.POSITIVE: 1.0,
            FeedbackType.IMPROVEMENT: 0.7,
            FeedbackType.CORRECTION: 0.3,
            FeedbackType.NEGATIVE: 0.1,
            FeedbackType.BUG_REPORT: 0.0
        }
        
        total_weight = 0
        weighted_score = 0
        
        for feedback in feedbacks:
            weight = weights.get(feedback.feedback_type, 0.5)
            total_weight += 1
            weighted_score += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.5

# Instância global
human_learning_system = HumanInLoopLearning()

def get_human_learning_system() -> HumanInLoopLearning:
    """Retorna instância do sistema de aprendizado humano"""
    return human_learning_system

def capture_user_feedback(query: str, response: str, feedback: str, 
                         feedback_type: str = "improvement", severity: str = "medium",
                         context: Optional[Dict[str, Any]] = None) -> str:
    """Função helper para capturar feedback do usuário"""
    
    learning_system = get_human_learning_system()
    return learning_system.capture_feedback(query, response, feedback, feedback_type, severity, context)

def get_learning_insights(days: int = 7) -> Dict[str, Any]:
    """Função helper para obter insights de aprendizado"""
    
    learning_system = get_human_learning_system()
    return learning_system.generate_learning_report(days) 