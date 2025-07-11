"""
📊 ANALYZERS - Módulo de Análise
==============================

Módulo responsável por análise de dados e consultas.
"""

import logging

logger = logging.getLogger(__name__)

# Flask fallback para execução standalone
try:
    from app.claude_ai_novo.utils.flask_fallback import is_flask_available
    flask_available = is_flask_available()
except ImportError:
    flask_available = False
    logger.warning("Flask fallback não disponível")

# Imports condicionais - Módulos existentes
try:
    from .intention_analyzer import IntentionAnalyzer  # type: ignore[assignment]
    from .query_analyzer import QueryAnalyzer  # type: ignore[assignment]
    from .metacognitive_analyzer import MetacognitiveAnalyzer  # type: ignore[assignment]
    from .nlp_enhanced_analyzer import NLPEnhancedAnalyzer  # type: ignore[assignment]
    from .analyzer_manager import AnalyzerManager  # type: ignore[assignment]
    from .diagnostics_analyzer import DiagnosticsAnalyzer, get_diagnostics_analyzer  # type: ignore[assignment]
    from .structural_analyzer import StructuralAnalyzer, get_structural_analyzer  # type: ignore[assignment]
    from .semantic_analyzer import SemanticAnalyzer, get_semantic_analyzer  # type: ignore[assignment]
    from .performance_analyzer import PerformanceAnalyzer, get_performance_analyzer  # type: ignore[assignment]
    
    logger.info("✅ Analyzers carregados com sucesso")
    
except ImportError as e:
    logger.warning(f"⚠️ Erro ao carregar analyzers: {e}")
    
    # Fallback classes para módulos existentes
    class IntentionAnalyzer:
        def __init__(self): pass
        def analyze(self, query): return {"intention": "unknown", "confidence": 0.0}
    
    class QueryAnalyzer:
        def __init__(self): pass
        def analyze(self, query): return {"type": "unknown", "fields": []}
    
    class MetacognitiveAnalyzer:
        def __init__(self): pass
        def analyze_own_performance(self, query, response, context): return {"confidence": 0.5}
    
    class NLPEnhancedAnalyzer:
        def __init__(self): pass
        def analyze_text(self, text): return {"tokens": text.split(), "word_count": len(text.split())}
    
    # Fallback classes para novos módulos
    class StructuralAnalyzer:
        def __init__(self): pass
        def analyze_structure(self, data): return {"status": "fallback", "structure_quality": "unknown"}
        def validate_architecture(self, data): return {"status": "fallback", "score": 0}
        def detect_patterns(self, data): return {"detected_patterns": [], "complexity_score": 0}
    
    class SemanticAnalyzer:
        def __init__(self): pass
        def analyze_query(self, query): return {"analysis_type": "semantic", "status": "fallback", "confidence": 0.0}
        def extract_entities(self, text): return {}
        def classify_intent(self, query, context=None): return {"primary_intent": "unknown", "confidence": 0.0}
    
    class PerformanceAnalyzer:
        def __init__(self): pass
        def analyze_ai_performance(self, days=30): return {"status": "fallback", "message": "Performance analysis não disponível"}
        def analyze_user_behavior(self, user_id=None, days=30): return {"status": "fallback", "message": "Behavior analysis não disponível"}
        def detect_anomalies(self, days=7): return {"status": "fallback", "message": "Anomaly detection não disponível"}
    
    class DiagnosticsAnalyzer:
        def __init__(self, orchestrator=None): pass
        def analyze_diagnostics(self): return {"status": "fallback", "message": "Diagnostics não disponível"}
    
    class AnalyzerManager:
        def __init__(self): 
            self.intention_analyzer = IntentionAnalyzer()
            self.query_analyzer = QueryAnalyzer()
            self.structural_analyzer = StructuralAnalyzer()
            self.semantic_analyzer = SemanticAnalyzer()
            self.performance_analyzer = PerformanceAnalyzer()
        def analyze_query(self, query): return {"analyzed": True}
    
    # Funções de conveniência para fallback
    def get_structural_analyzer():
        return StructuralAnalyzer()
    
    def get_semantic_analyzer():
        return SemanticAnalyzer()

def get_analyzer_manager():
    """Retorna instância do AnalyzerManager"""
    return AnalyzerManager()

def get_intention_analyzer():
    """Retorna instância do IntentionAnalyzer"""
    return IntentionAnalyzer()

def get_query_analyzer():
    """Retorna instância do QueryAnalyzer"""
    return QueryAnalyzer()

def get_metacognitive_analyzer():
    """Retorna instância do MetacognitiveAnalyzer"""
    return MetacognitiveAnalyzer()

def get_nlp_enhanced_analyzer():
    """Retorna instância do NLPEnhancedAnalyzer"""
    return NLPEnhancedAnalyzer()

def get_diagnostics_analyzer(orchestrator=None):
    """Retorna instância do DiagnosticsAnalyzer"""
    try:
        from .diagnostics_analyzer import DiagnosticsAnalyzer
        if orchestrator:
            return DiagnosticsAnalyzer(orchestrator)
        else:
            logger.warning("DiagnosticsAnalyzer requer orchestrator")
            return None
    except ImportError:
        logger.warning("DiagnosticsAnalyzer não disponível")
        return None

def get_performance_analyzer():
    """Retorna instância do PerformanceAnalyzer"""
    try:
        from .performance_analyzer import PerformanceAnalyzer
        return PerformanceAnalyzer()
    except ImportError:
        logger.warning("PerformanceAnalyzer não disponível")
        return PerformanceAnalyzer()  # Fallback class

# Funções de conveniência para análise rápida
def analyze_query_intention(query: str):
    """Análise rápida de intenção"""
    analyzer = get_intention_analyzer()
    return analyzer.analyze(query)

def analyze_text_structure(data: dict):
    """Análise rápida de estrutura"""
    analyzer = get_structural_analyzer()
    return analyzer.analyze_structure(data)

def analyze_semantic_meaning(query: str):
    """Análise rápida semântica"""
    analyzer = get_semantic_analyzer()
    return analyzer.analyze_query(query)

__all__ = [
    # Classes principais
    'IntentionAnalyzer',
    'QueryAnalyzer', 
    'MetacognitiveAnalyzer',
    'NLPEnhancedAnalyzer',
    'StructuralAnalyzer',
    'SemanticAnalyzer',
    'DiagnosticsAnalyzer',
    'AnalyzerManager',
    'PerformanceAnalyzer',
    
    # Funções de conveniência
    'get_analyzer_manager',
    'get_intention_analyzer',
    'get_query_analyzer',
    'get_metacognitive_analyzer',
    'get_nlp_enhanced_analyzer',
    'get_structural_analyzer',
    'get_semantic_analyzer',
    'get_diagnostics_analyzer',
    'get_performance_analyzer',
    
    # Funções de análise rápida
    'analyze_query_intention',
    'analyze_text_structure',
    'analyze_semantic_meaning'
]