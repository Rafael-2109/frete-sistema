"""
📊 PERFORMANCE ANALYZER - Analytics Avançadas de Desempenho
=========================================================

Responsabilidade: ANALISAR dados de performance e gerar insights avançados.
Especializações: Métricas IA, Padrões de Uso, Performance Temporal, Insights Preditivos.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from collections import defaultdict
import statistics

# Imports internos com fallbacks robustos
try:
    from ..utils.flask_fallback import get_db
except ImportError:
    # Fallback para execução standalone
    try:
        from utils.flask_fallback import get_db
    except ImportError:
        # Fallback final para quando Flask não disponível
        def get_db():
            logger.warning("⚠️ get_db() não disponível - modo limitado")
            return None

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    Especialista em analisar performance e gerar analytics avançadas.
    
    Responsabilidades:
    - Analisar métricas de performance IA
    - Detectar padrões de uso e comportamento
    - Gerar insights preditivos
    - Monitorar tendências temporais
    """
    
    def __init__(self):
        """Inicializa o analisador de performance."""
        self.db = get_db()
        self.session_table = "ai_advanced_sessions"
        self._ensure_table_exists()
        logger.info("📊 PerformanceAnalyzer inicializado")
    
    def _ensure_table_exists(self):
        """Verifica se tabela existe, cria avisos se necessário."""
        try:
            if self.db is None:
                logger.warning("⚠️ Banco de dados não disponível - PerformanceAnalyzer em modo limitado")
                return
                
            # Verificar se tabela existe
            check_query = text("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = :table_name
            """)
            result = self.db.session.execute(check_query, {'table_name': self.session_table}).fetchone()
            
            if not result:
                logger.warning(f"⚠️ Tabela {self.session_table} não existe - análises serão limitadas")
                logger.info("💡 Para análises completas, execute as migrações do sistema avançado")
            else:
                logger.info(f"✅ Tabela {self.session_table} encontrada - análises completas disponíveis")
                
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível verificar tabela {self.session_table}: {e}")
            logger.info("💡 PerformanceAnalyzer funcionará em modo limitado")
    
    def analyze_ai_performance(self, days: int = 30) -> Dict[str, Any]:
        """
        Analisa performance geral dos sistemas IA.
        
        Args:
            days: Período em dias para análise
            
        Returns:
            Análise completa de performance
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Query principal para métricas
            query = text(f"""
                SELECT 
                    metadata_jsonb->>'$.confidence' as confidence,
                    metadata_jsonb->>'$.domain' as domain,
                    metadata_jsonb->>'$.complexity' as complexity,
                    metadata_jsonb->>'$.processing_time' as processing_time,
                    metadata_jsonb->>'$.model_used' as model_used,
                    metadata_jsonb->>'$.tokens_used' as tokens_used,
                    metadata_jsonb->>'$.success' as success,
                    created_at,
                    user_id
                FROM {self.session_table}
                WHERE created_at >= :cutoff_date
                  AND metadata_jsonb IS NOT NULL
                ORDER BY created_at DESC
            """)
            
            results = self.db.session.execute(query, {'cutoff_date': cutoff_date}).fetchall()
            
            if not results:
                return {
                    'period_days': days,
                    'total_sessions': 0,
                    'message': 'Nenhuma sessão encontrada no período',
                    'generated_at': datetime.now().isoformat()
                }
            
            # Processar dados
            confidences = []
            domains = defaultdict(int)
            complexities = defaultdict(int)
            processing_times = []
            models = defaultdict(int)
            tokens_usage = []
            success_count = 0
            hourly_distribution: Dict[int, int] = defaultdict(int)
            daily_trend: Dict[str, int] = defaultdict(int)
            
            for row in results:
                # Confidence
                try:
                    if row.confidence:
                        confidences.append(float(row.confidence))
                except (ValueError, TypeError):
                    pass
                
                # Domain
                if row.domain:
                    domains[row.domain] += 1
                
                # Complexity
                if row.complexity:
                    complexities[row.complexity] += 1
                
                # Processing time
                try:
                    if row.processing_time:
                        processing_times.append(float(row.processing_time))
                except (ValueError, TypeError):
                    pass
                
                # Model used
                if row.model_used:
                    models[row.model_used] += 1
                
                # Tokens usage
                try:
                    if row.tokens_used:
                        tokens_usage.append(int(row.tokens_used))
                except (ValueError, TypeError):
                    pass
                
                # Success rate
                if row.success and str(row.success).lower() == 'true':
                    success_count += 1
                
                # Temporal patterns
                if row.created_at:
                    hour = row.created_at.hour
                    day = row.created_at.date().isoformat()
                    hourly_distribution[hour] += 1
                    daily_trend[day] += 1
            
            # Calcular métricas
            total_sessions = len(results)
            avg_confidence = statistics.mean(confidences) if confidences else 0
            avg_processing_time = statistics.mean(processing_times) if processing_times else 0
            avg_tokens = statistics.mean(tokens_usage) if tokens_usage else 0
            success_rate = (success_count / total_sessions) * 100
            
            # Detectar padrões
            peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else 0
            most_used_domain = max(domains.items(), key=lambda x: x[1])[0] if domains else 'N/A'
            most_used_model = max(models.items(), key=lambda x: x[1])[0] if models else 'N/A'
            
            # Trends analysis
            trend_analysis = self._analyze_trends(daily_trend)
            
            return {
                'period_days': days,
                'total_sessions': total_sessions,
                'success_rate': round(success_rate, 2),
                'confidence_metrics': {
                    'average': round(avg_confidence, 3),
                    'median': round(statistics.median(confidences), 3) if confidences else 0,
                    'std_dev': round(statistics.stdev(confidences), 3) if len(confidences) > 1 else 0,
                    'distribution': self._create_distribution(confidences, 'confidence')
                },
                'performance_metrics': {
                    'avg_processing_time': round(avg_processing_time, 2),
                    'avg_tokens_used': round(avg_tokens, 0),
                    'processing_time_distribution': self._create_distribution(processing_times, 'time')
                },
                'usage_patterns': {
                    'domains': dict(domains),
                    'most_used_domain': most_used_domain,
                    'complexity_distribution': dict(complexities),
                    'models_used': dict(models),
                    'most_used_model': most_used_model
                },
                'temporal_patterns': {
                    'peak_hour': peak_hour,
                    'hourly_distribution': dict(hourly_distribution),
                    'daily_trend': dict(daily_trend),
                    'trend_analysis': trend_analysis
                },
                'insights': self._generate_insights(
                    avg_confidence, success_rate, most_used_domain, 
                    avg_processing_time, trend_analysis
                ),
                'generated_at': datetime.now().isoformat()
            }
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao analisar performance: {e}")
            return {
                'error': str(e),
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
    
    def analyze_user_behavior(self, user_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """
        Analisa comportamento de usuários específicos ou geral.
        
        Args:
            user_id: ID do usuário (None para análise geral)
            days: Período em dias para análise
            
        Returns:
            Análise de comportamento do usuário
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Query base
            where_clause = "WHERE created_at >= :cutoff_date"
            params: Dict[str, Any] = {'cutoff_date': cutoff_date}
            
            if user_id:
                where_clause += " AND user_id = :user_id"
                params['user_id'] = str(user_id)
            
            query = text(f"""
                SELECT 
                    user_id,
                    COUNT(*) as session_count,
                    AVG(CASE WHEN metadata_jsonb->>'$.confidence' IS NOT NULL 
                        THEN (metadata_jsonb->>'$.confidence')::float 
                        ELSE NULL END) as avg_confidence,
                    STRING_AGG(DISTINCT metadata_jsonb->>'$.domain', ', ') as domains_used,
                    MIN(created_at) as first_session,
                    MAX(created_at) as last_session,
                    COUNT(DISTINCT DATE(created_at)) as active_days
                FROM {self.session_table}
                {where_clause}
                GROUP BY user_id
                ORDER BY session_count DESC
                LIMIT 20
            """)
            
            results = self.db.session.execute(query, params).fetchall()
            
            if not results:
                return {
                    'user_id': user_id,
                    'period_days': days,
                    'message': 'Nenhum dado encontrado',
                    'generated_at': datetime.now().isoformat()
                }
            
            # Processar resultados
            user_behaviors = []
            for row in results:
                engagement_score = self._calculate_engagement_score(
                    row.session_count, row.active_days, days
                )
                
                user_behaviors.append({
                    'user_id': row.user_id,
                    'session_count': row.session_count,
                    'avg_confidence': round(row.avg_confidence or 0, 3),
                    'domains_used': row.domains_used or 'N/A',
                    'first_session': row.first_session.isoformat() if row.first_session else None,
                    'last_session': row.last_session.isoformat() if row.last_session else None,
                    'active_days': row.active_days,
                    'engagement_score': engagement_score,
                    'engagement_level': self._get_engagement_level(engagement_score)
                })
            
            # Estatísticas gerais
            total_users = len(user_behaviors)
            avg_sessions_per_user = statistics.mean([u['session_count'] for u in user_behaviors])
            power_users = len([u for u in user_behaviors if u['engagement_level'] == 'Alto'])
            
            return {
                'user_id': user_id,
                'period_days': days,
                'total_users': total_users,
                'avg_sessions_per_user': round(avg_sessions_per_user, 1),
                'power_users_count': power_users,
                'user_behaviors': user_behaviors,
                'behavior_insights': self._generate_behavior_insights(user_behaviors),
                'generated_at': datetime.now().isoformat()
            }
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao analisar comportamento: {e}")
            return {
                'error': str(e),
                'user_id': user_id,
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
    
    def detect_anomalies(self, days: int = 7) -> Dict[str, Any]:
        """
        Detecta anomalias na performance dos sistemas.
        
        Args:
            days: Período em dias para análise
            
        Returns:
            Análise de anomalias detectadas
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Query para dados detalhados
            query = text(f"""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as daily_sessions,
                    AVG(CASE WHEN metadata_jsonb->>'$.confidence' IS NOT NULL 
                        THEN (metadata_jsonb->>'$.confidence')::float 
                        ELSE NULL END) as avg_confidence,
                    AVG(CASE WHEN metadata_jsonb->>'$.processing_time' IS NOT NULL 
                        THEN (metadata_jsonb->>'$.processing_time')::float 
                        ELSE NULL END) as avg_processing_time,
                    COUNT(CASE WHEN metadata_jsonb->>'$.success' = 'false' THEN 1 END) as failures
                FROM {self.session_table}
                WHERE created_at >= :cutoff_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            
            results = self.db.session.execute(query, {'cutoff_date': cutoff_date}).fetchall()
            
            if len(results) < 2:
                return {
                    'period_days': days,
                    'message': 'Dados insuficientes para análise de anomalias',
                    'generated_at': datetime.now().isoformat()
                }
            
            # Processar dados
            daily_data = []
            for row in results:
                daily_data.append({
                    'date': row.date.isoformat(),
                    'sessions': row.daily_sessions,
                    'avg_confidence': float(row.avg_confidence or 0),
                    'avg_processing_time': float(row.avg_processing_time or 0),
                    'failures': row.failures
                })
            
            # Detectar anomalias
            anomalies = self._detect_statistical_anomalies(daily_data)
            
            return {
                'period_days': days,
                'daily_data': daily_data,
                'anomalies_detected': anomalies,
                'anomaly_summary': self._summarize_anomalies(anomalies),
                'generated_at': datetime.now().isoformat()
            }
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao detectar anomalias: {e}")
            return {
                'error': str(e),
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
    
    def _analyze_trends(self, daily_data: Dict[str, int]) -> Dict[str, Any]:
        """Analisa tendências temporais."""
        if len(daily_data) < 3:
            return {'trend': 'insufficient_data', 'direction': 'unknown'}
        
        # Converter chaves para strings se necessário
        sorted_keys = sorted(daily_data.keys())
        values = [daily_data[key] for key in sorted_keys]
        
        # Calcular tendência simples
        if len(values) >= 2:
            recent_avg = statistics.mean(values[-3:])
            older_avg = statistics.mean(values[:-3]) if len(values) > 3 else values[0]
            
            if recent_avg > older_avg * 1.2:
                trend = 'increasing'
            elif recent_avg < older_avg * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'recent_avg': round(statistics.mean(values[-3:]), 1),
            'overall_avg': round(statistics.mean(values), 1),
            'max_value': max(values),
            'min_value': min(values)
        }
    
    def _create_distribution(self, values: List[float], data_type: str) -> Dict[str, int]:
        """Cria distribuição de valores."""
        if not values:
            return {}
        
        if data_type == 'confidence':
            buckets = {'0.0-0.3': 0, '0.3-0.6': 0, '0.6-0.8': 0, '0.8-1.0': 0}
            for val in values:
                if val < 0.3:
                    buckets['0.0-0.3'] += 1
                elif val < 0.6:
                    buckets['0.3-0.6'] += 1
                elif val < 0.8:
                    buckets['0.6-0.8'] += 1
                else:
                    buckets['0.8-1.0'] += 1
        elif data_type == 'time':
            buckets = {'<1s': 0, '1-3s': 0, '3-10s': 0, '>10s': 0}
            for val in values:
                if val < 1:
                    buckets['<1s'] += 1
                elif val < 3:
                    buckets['1-3s'] += 1
                elif val < 10:
                    buckets['3-10s'] += 1
                else:
                    buckets['>10s'] += 1
        else:
            buckets = {}
        
        return buckets
    
    def _calculate_engagement_score(self, sessions: int, active_days: int, period_days: int) -> float:
        """Calcula score de engajamento do usuário."""
        frequency_score = min(sessions / period_days, 1.0)  # Máximo 1 sessão por dia
        consistency_score = active_days / period_days
        return round((frequency_score + consistency_score) / 2, 3)
    
    def _get_engagement_level(self, score: float) -> str:
        """Determina nível de engajamento."""
        if score >= 0.7:
            return 'Alto'
        elif score >= 0.4:
            return 'Médio'
        else:
            return 'Baixo'
    
    def _generate_insights(self, avg_confidence: float, success_rate: float, 
                          most_used_domain: str, avg_processing_time: float, 
                          trend_analysis: Dict[str, Any]) -> List[str]:
        """Gera insights baseados nas métricas."""
        insights = []
        
        # Insights de confidence
        if avg_confidence >= 0.8:
            insights.append("🎯 Excelente nível de confiança das respostas")
        elif avg_confidence >= 0.6:
            insights.append("✅ Bom nível de confiança, com margem para melhoria")
        else:
            insights.append("⚠️ Nível de confiança baixo, revisar qualidade das respostas")
        
        # Insights de success rate
        if success_rate >= 95:
            insights.append("🏆 Taxa de sucesso excelente")
        elif success_rate >= 85:
            insights.append("✅ Taxa de sucesso satisfatória")
        else:
            insights.append("🔧 Taxa de sucesso requer atenção")
        
        # Insights de domain
        if most_used_domain != 'N/A':
            insights.append(f"📊 Domínio mais utilizado: {most_used_domain}")
        
        # Insights de performance
        if avg_processing_time < 2:
            insights.append("⚡ Tempo de processamento excelente")
        elif avg_processing_time < 5:
            insights.append("🔄 Tempo de processamento satisfatório")
        else:
            insights.append("🐌 Tempo de processamento pode ser otimizado")
        
        # Insights de trend
        if trend_analysis['trend'] == 'increasing':
            insights.append("📈 Tendência de crescimento no uso")
        elif trend_analysis['trend'] == 'decreasing':
            insights.append("📉 Tendência de redução no uso")
        
        return insights
    
    def _generate_behavior_insights(self, user_behaviors: List[Dict[str, Any]]) -> List[str]:
        """Gera insights sobre comportamento dos usuários."""
        insights = []
        
        if not user_behaviors:
            return insights
        
        # Análise de engajamento
        high_engagement = len([u for u in user_behaviors if u['engagement_level'] == 'Alto'])
        total_users = len(user_behaviors)
        
        if high_engagement / total_users >= 0.3:
            insights.append("🎉 Boa taxa de usuários altamente engajados")
        else:
            insights.append("📊 Oportunidade de aumentar engajamento dos usuários")
        
        # Análise de diversidade de uso
        unique_domains = set()
        for user in user_behaviors:
            if user['domains_used'] != 'N/A':
                unique_domains.update(user['domains_used'].split(', '))
        
        if len(unique_domains) >= 3:
            insights.append("🌐 Boa diversidade de domínios utilizados")
        
        # Top performer
        if user_behaviors:
            top_user = user_behaviors[0]
            insights.append(f"👑 Usuário mais ativo: {top_user['session_count']} sessões")
        
        return insights
    
    def _detect_statistical_anomalies(self, daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detecta anomalias estatísticas nos dados."""
        anomalies = []
        
        if len(daily_data) < 3:
            return anomalies
        
        # Extrair métricas
        sessions = [d['sessions'] for d in daily_data]
        confidences = [d['avg_confidence'] for d in daily_data]
        processing_times = [d['avg_processing_time'] for d in daily_data]
        
        # Calcular thresholds (2 desvios padrão)
        def detect_outliers(values: List[float], metric_name: str) -> List[Tuple[int, float]]:
            if len(values) < 3:
                return []
            
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values)
            threshold = 2 * std_val
            
            outliers = []
            for i, val in enumerate(values):
                if abs(val - mean_val) > threshold:
                    outliers.append((i, val))
            
            return outliers
        
        # Detectar anomalias por métrica
        for metric, values in [('sessions', sessions), ('confidence', confidences), ('processing_time', processing_times)]:
            outliers = detect_outliers(values, metric)
            for idx, val in outliers:
                anomalies.append({
                    'date': daily_data[idx]['date'],
                    'metric': metric,
                    'value': val,
                    'severity': 'high' if abs(val - statistics.mean(values)) > 3 * statistics.stdev(values) else 'medium'
                })
        
        return anomalies
    
    def _summarize_anomalies(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sumariza anomalias detectadas."""
        if not anomalies:
            return {'total': 0, 'message': 'Nenhuma anomalia detectada'}
        
        by_severity = defaultdict(int)
        by_metric = defaultdict(int)
        
        for anomaly in anomalies:
            by_severity[anomaly['severity']] += 1
            by_metric[anomaly['metric']] += 1
        
        return {
            'total': len(anomalies),
            'by_severity': dict(by_severity),
            'by_metric': dict(by_metric),
            'requires_attention': any(a['severity'] == 'high' for a in anomalies)
        }


# Instância global para conveniência
_performance_analyzer = None

def get_performance_analyzer() -> PerformanceAnalyzer:
    """
    Retorna instância global do PerformanceAnalyzer.
    
    Returns:
        Instância do PerformanceAnalyzer
    """
    global _performance_analyzer
    if _performance_analyzer is None:
        _performance_analyzer = PerformanceAnalyzer()
    return _performance_analyzer

def analyze_system_performance(days: int = 30) -> Dict[str, Any]:
    """
    Função de conveniência para análise de performance.
    
    Args:
        days: Período em dias para análise
        
    Returns:
        Análise completa de performance
    """
    return get_performance_analyzer().analyze_ai_performance(days)

def detect_system_anomalies(days: int = 7) -> Dict[str, Any]:
    """
    Função de conveniência para detectar anomalias do sistema.
    
    Args:
        days: Período em dias para análise
        
    Returns:
        Análise de anomalias detectadas
    """
    analyzer = get_performance_analyzer()
    return analyzer.detect_anomalies(days)

def classify_api_performance(score: float) -> str:
    """
    Classifica performance de APIs externas.
    
    Args:
        score: Score de performance (0.0 a 1.0)
        
    Returns:
        Classificação textual da performance
    """
    if score >= 0.9:
        return "EXCELENTE"
    elif score >= 0.7:
        return "BOA"
    elif score >= 0.5:
        return "LIMITADA"
    else:
        return "CRÍTICA" 