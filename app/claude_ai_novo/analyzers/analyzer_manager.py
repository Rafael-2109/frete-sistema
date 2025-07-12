#!/usr/bin/env python3
"""
AnalyzerManager - Coordenar múltiplos analyzers (NLP, intenção, contexto, estrutural, semântico)
Atualizado para incluir os novos módulos structural_analyzer e semantic_analyzer
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncio
from datetime import datetime

# Imports dos componentes reais com fallbacks
try:
    from app.claude_ai_novo.analyzers.intention_analyzer import IntentionAnalyzer as RealIntentionAnalyzer
    IntentionAnalyzer = RealIntentionAnalyzer
except ImportError:
    class FallbackIntentionAnalyzer:
        """Fallback para IntentionAnalyzer"""
        def __init__(self):
            pass
        def analyze_intention(self, query): return {"intention": "unknown", "confidence": 0.0}
    IntentionAnalyzer = FallbackIntentionAnalyzer

try:
    from app.claude_ai_novo.analyzers.nlp_enhanced_analyzer import NLPEnhancedAnalyzer as RealNLPEnhancedAnalyzer
    NLPEnhancedAnalyzer = RealNLPEnhancedAnalyzer
except ImportError:
    class FallbackNLPEnhancedAnalyzer:
        """Fallback para NLPEnhancedAnalyzer"""
        def __init__(self):
            pass
        def analyze_text(self, text): return {"tokens": text.split(), "word_count": len(text.split())}
    NLPEnhancedAnalyzer = FallbackNLPEnhancedAnalyzer

try:
    from app.claude_ai_novo.analyzers.query_analyzer import QueryAnalyzer as RealQueryAnalyzer
    QueryAnalyzer = RealQueryAnalyzer
except ImportError:
    class FallbackQueryAnalyzer:
        """Fallback para QueryAnalyzer"""
        def __init__(self):
            pass
        def analyze_query(self, query): return {"type": "unknown", "fields": []}
    QueryAnalyzer = FallbackQueryAnalyzer

try:
    from app.claude_ai_novo.analyzers.metacognitive_analyzer import MetacognitiveAnalyzer as RealMetacognitiveAnalyzer
    MetacognitiveAnalyzer = RealMetacognitiveAnalyzer
except ImportError:
    class FallbackMetacognitiveAnalyzer:
        """Fallback para MetacognitiveAnalyzer"""
        def __init__(self):
            pass
        def analyze_own_performance(self, query, response, context): return {"confidence": 0.5}
    MetacognitiveAnalyzer = FallbackMetacognitiveAnalyzer

# Novos módulos criados
try:
    from app.claude_ai_novo.analyzers.structural_analyzer import StructuralAnalyzer as RealStructuralAnalyzer
    StructuralAnalyzer = RealStructuralAnalyzer
except ImportError:
    class FallbackStructuralAnalyzer:
        """Fallback para StructuralAnalyzer"""
        def __init__(self):
            pass
        def analyze_structure(self, data): return {"status": "fallback", "structure_quality": "unknown"}
        def validate_architecture(self, data): return {"status": "fallback", "score": 0}
        def detect_patterns(self, data): return {"detected_patterns": [], "complexity_score": 0}
    StructuralAnalyzer = FallbackStructuralAnalyzer

try:
    from app.claude_ai_novo.analyzers.semantic_analyzer import SemanticAnalyzer as RealSemanticAnalyzer
    SemanticAnalyzer = RealSemanticAnalyzer
except ImportError:
    class FallbackSemanticAnalyzer:
        """Fallback para SemanticAnalyzer"""
        def __init__(self):
            pass
        def analyze_query(self, query): return {"analysis_type": "semantic", "status": "fallback", "confidence": 0.0}
        def extract_entities(self, text): return {}
        def classify_intent(self, query, context=None): return {"primary_intent": "unknown", "confidence": 0.0}
    SemanticAnalyzer = FallbackSemanticAnalyzer

try:
    from app.claude_ai_novo.analyzers.diagnostics_analyzer import DiagnosticsAnalyzer as RealDiagnosticsAnalyzer
    DiagnosticsAnalyzer = RealDiagnosticsAnalyzer
except ImportError:
    class FallbackDiagnosticsAnalyzer:
        """Fallback para DiagnosticsAnalyzer"""
        def __init__(self, orchestrator=None):
            pass
        def gerar_estatisticas_completas(self): return {"status": "fallback", "estatisticas": {}}
        def diagnosticar_qualidade(self): return {"status": "fallback", "qualidade": "unknown"}
        def gerar_relatorio_resumido(self): return {"status": "fallback", "resumo": {}}
    DiagnosticsAnalyzer = FallbackDiagnosticsAnalyzer

# Import da classe base centralizada
from app.claude_ai_novo.utils.base_context_manager import BaseContextManager

logger = logging.getLogger(__name__)

class AnalyzerManager(BaseContextManager):
    """
    Coordenar múltiplos analyzers (NLP, intenção, contexto, estrutural, semântico)
    
    Gerencia e coordena todos os componentes da pasta analyzer incluindo os novos módulos
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.AnalyzerManager")
        self.components = {}
        self.initialized = False
        self._initialized = True  # Marcar como inicializado no contexto base
        
        # Inicializar componentes
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa todos os componentes gerenciados"""
        
        try:
            # Inicializar IntentionAnalyzer
            try:
                self.components['intention'] = IntentionAnalyzer()
                self.logger.debug(f"IntentionAnalyzer inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar IntentionAnalyzer: {e}")
                self.components['intention'] = None

            # Inicializar NLPEnhancedAnalyzer
            try:
                self.components['nlpenhanced'] = NLPEnhancedAnalyzer()
                self.logger.debug(f"NLPEnhancedAnalyzer inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar NLPEnhancedAnalyzer: {e}")
                self.components['nlpenhanced'] = None

            # Inicializar QueryAnalyzer
            try:
                self.components['query'] = QueryAnalyzer()
                self.logger.debug(f"QueryAnalyzer inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar QueryAnalyzer: {e}")
                self.components['query'] = None

            # Inicializar MetacognitiveAnalyzer
            try:
                self.components['metacognitive'] = MetacognitiveAnalyzer()
                self.logger.debug(f"MetacognitiveAnalyzer inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar MetacognitiveAnalyzer: {e}")
                self.components['metacognitive'] = None

            # Inicializar StructuralAnalyzer (NOVO)
            try:
                self.components['structural'] = StructuralAnalyzer()
                self.logger.debug(f"StructuralAnalyzer inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar StructuralAnalyzer: {e}")
                self.components['structural'] = None

            # Inicializar SemanticAnalyzer (NOVO)
            try:
                self.components['semantic'] = SemanticAnalyzer()
                self.logger.debug(f"SemanticAnalyzer inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar SemanticAnalyzer: {e}")
                self.components['semantic'] = None

            # Inicializar DiagnosticsAnalyzer (requer orchestrator - será None por enquanto)
            try:
                self.components['diagnostics'] = None  # Será inicializado quando orchestrator estiver disponível
                self.logger.debug(f"DiagnosticsAnalyzer preparado (aguardando orchestrator)")
            except Exception as e:
                self.logger.warning(f"Erro ao preparar DiagnosticsAnalyzer: {e}")
                self.components['diagnostics'] = None

            self.initialized = True
            self.logger.info(f"AnalyzerManager inicializado com sucesso - {len([c for c in self.components.values() if c is not None])}/{len(self.components)} componentes ativos")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar AnalyzerManager: {e}")
            raise
    
    def analyze_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analisa consulta usando múltiplos analyzers de forma coordenada e inteligente
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional
            
        Returns:
            Dict com análise completa coordenada
        """
        
        if not self.initialized:
            raise RuntimeError(f"AnalyzerManager não foi inicializado")
        
        try:
            self.logger.debug(f"🔍 Analisando consulta: {query[:50]}...")
            
            # Análise coordenada usando múltiplos analyzers
            resultado = {
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'components_used': [],
                'analysis_complete': True,
                'analysis_strategy': 'intelligent_coordination'
            }
            
            # 1. Análise semântica (sempre primeiro para entender o contexto)
            if self.components.get('semantic'):
                try:
                    semantic_result = self.components['semantic'].analyze_query(query)
                    resultado['semantic_analysis'] = semantic_result
                    resultado['components_used'].append('semantic')
                    self.logger.debug("✅ Análise semântica concluída")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro na análise semântica: {e}")
                    resultado['semantic_analysis'] = {'error': str(e)}

            # 2. Análise de intenção (baseada no contexto semântico)
            if self.components.get('intention'):
                try:
                    intention_result = self.components['intention'].analyze_intention(query)
                    resultado['intention_analysis'] = intention_result
                    resultado['components_used'].append('intention')
                    self.logger.debug("✅ Análise de intenção concluída")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro na análise de intenção: {e}")
                    resultado['intention_analysis'] = {'error': str(e)}
            
            # 3. Análise estrutural da query
            if self.components.get('query'):
                try:
                    query_result = self.components['query'].analyze_query(query)
                    resultado['query_analysis'] = query_result
                    resultado['components_used'].append('query')
                    self.logger.debug("✅ Análise estrutural da query concluída")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro na análise da query: {e}")
                    resultado['query_analysis'] = {'error': str(e)}
            
            # 4. Análise NLP avançada (se necessário - consultas complexas)
            usar_nlp = self._should_use_nlp_analysis(query, resultado)
            
            if usar_nlp and self.components.get('nlpenhanced'):
                try:
                    nlp_result = self.components['nlpenhanced'].analyze_text(query)
                    resultado['nlp_analysis'] = nlp_result
                    resultado['components_used'].append('nlpenhanced')
                    self.logger.debug("✅ Análise NLP avançada concluída")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro na análise NLP: {e}")
                    resultado['nlp_analysis'] = {'error': str(e)}
            
            # 5. Análise estrutural de dados (se contexto fornecido)
            if context and self.components.get('structural'):
                try:
                    structural_result = self.components['structural'].analyze_structure(context)
                    resultado['structural_analysis'] = structural_result
                    resultado['components_used'].append('structural')
                    self.logger.debug("✅ Análise estrutural de dados concluída")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro na análise estrutural: {e}")
                    resultado['structural_analysis'] = {'error': str(e)}
            
            # 6. Análise metacognitiva (sempre por último para avaliar todas as análises)
            if self.components.get('metacognitive'):
                try:
                    meta_result = self.components['metacognitive'].analyze_own_performance(
                        query, str(resultado), context or {}
                    )
                    resultado['metacognitive_analysis'] = meta_result
                    resultado['components_used'].append('metacognitive')
                    self.logger.debug("✅ Análise metacognitiva concluída")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro na análise metacognitiva: {e}")
                    resultado['metacognitive_analysis'] = {'error': str(e)}
            
            # Compilar resultado final com insights combinados
            resultado['total_components'] = len(resultado['components_used'])
            resultado['success'] = len(resultado['components_used']) > 0
            resultado['confidence_score'] = self._calculate_combined_confidence(resultado)
            resultado['combined_insights'] = self._generate_combined_insights(resultado)
            
            self.logger.info(f"🎯 Análise completa: {len(resultado['components_used'])} componentes usados, confiança: {resultado['confidence_score']:.2f}")
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise coordenada: {e}")
            return {
                'query': query,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }

    def _should_use_nlp_analysis(self, query: str, current_results: Dict[str, Any]) -> bool:
        """Determina se deve usar análise NLP avançada"""
        # Verificar complexidade da consulta
        if len(query.split()) > 15:
            return True
        
        # Verificar se análise semântica indica complexidade
        semantic_analysis = current_results.get('semantic_analysis', {})
        if semantic_analysis.get('confidence', 0) < 0.5:
            return True
        
        # Verificar se análise de intenção indica complexidade
        intention_analysis = current_results.get('intention_analysis', {})
        if intention_analysis.get('complexity') == 'high':
            return True
        
        # Verificar se contém múltiplas entidades
        entities = semantic_analysis.get('entities', {})
        if len(entities) > 3:
            return True
        
        return False

    def _calculate_combined_confidence(self, results: Dict[str, Any]) -> float:
        """Calcula confiança combinada de todas as análises"""
        confidences = []
        
        # Coletar todas as pontuações de confiança
        for analysis_key in ['semantic_analysis', 'intention_analysis', 'query_analysis', 'metacognitive_analysis']:
            analysis = results.get(analysis_key, {})
            if 'confidence' in analysis:
                confidences.append(analysis['confidence'])
            elif 'confidence_score' in analysis:
                confidences.append(analysis['confidence_score'])
        
        if not confidences:
            return 0.0
        
        # Média ponderada (análise semântica e de intenção têm peso maior)
        weights = [0.3, 0.3, 0.2, 0.2][:len(confidences)]
        weighted_sum = sum(conf * weight for conf, weight in zip(confidences, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _generate_combined_insights(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Gera insights combinados de todas as análises"""
        insights = {
            'primary_intent': 'unknown',
            'entities_found': [],
            'complexity_level': 'low',
            'recommendations': [],
            'structural_issues': []
        }
        
        # Extrair intenção primária
        semantic_analysis = results.get('semantic_analysis', {})
        intention_analysis = results.get('intention_analysis', {})
        
        if semantic_analysis.get('intent') != 'unknown':
            insights['primary_intent'] = semantic_analysis.get('intent', 'unknown')
        elif intention_analysis.get('intention') != 'unknown':
            insights['primary_intent'] = intention_analysis.get('intention', 'unknown')
        
        # Extrair entidades
        if 'entities' in semantic_analysis:
            insights['entities_found'] = semantic_analysis['entities']
        
        # Determinar complexidade
        nlp_used = 'nlpenhanced' in results.get('components_used', [])
        if nlp_used:
            insights['complexity_level'] = 'high'
        elif len(results.get('components_used', [])) > 3:
            insights['complexity_level'] = 'medium'
        
        # Gerar recomendações
        if results.get('confidence_score', 0) < 0.5:
            insights['recommendations'].append("Consulta pode precisar de mais contexto")
        
        # Identificar problemas estruturais
        structural_analysis = results.get('structural_analysis', {})
        if structural_analysis.get('issues'):
            insights['structural_issues'] = structural_analysis['issues']
        
        return insights

    def initialize_diagnostics_analyzer(self, orchestrator):
        """
        Inicializa DiagnosticsAnalyzer quando orchestrator estiver disponível.
        
        Args:
            orchestrator: Instância do orchestrator necessária
        """
        try:
            if orchestrator:
                self.components['diagnostics'] = DiagnosticsAnalyzer(orchestrator)
                self.logger.info("✅ DiagnosticsAnalyzer inicializado com orchestrator")
            else:
                self.logger.warning("⚠️ Orchestrator não fornecido para DiagnosticsAnalyzer")
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar DiagnosticsAnalyzer: {e}")
            self.components['diagnostics'] = None

    def analyze_diagnostics(self, orchestrator=None) -> Dict[str, Any]:
        """
        Executa análise de diagnósticos usando DiagnosticsAnalyzer.
        
        Args:
            orchestrator: Instância do orchestrator (opcional, usa o já inicializado se disponível)
            
        Returns:
            Dict com análise de diagnósticos
        """
        try:
            # Se orchestrator foi fornecido e componente não inicializado, inicializar
            if orchestrator and not self.components.get('diagnostics'):
                self.initialize_diagnostics_analyzer(orchestrator)
            
            if self.components.get('diagnostics'):
                return {
                    'status': 'success',
                    'estatisticas': self.components['diagnostics'].gerar_estatisticas_completas(),
                    'qualidade': self.components['diagnostics'].diagnosticar_qualidade(),
                    'resumo': self.components['diagnostics'].gerar_relatorio_resumido()
                }
            else:
                return {
                    'error': 'DiagnosticsAnalyzer não disponível',
                    'fallback': True,
                    'status': 'unavailable'
                }
        except Exception as e:
            self.logger.error(f"❌ Erro na análise de diagnósticos: {e}")
            return {
                'error': str(e),
                'status': 'error'
            }

    # Métodos específicos para cada analyzer (mantidos para compatibilidade)
    def analyze_intention(self, query: str) -> Dict[str, Any]:
        """Delega análise de intenção para o IntentionAnalyzer"""
        if not self.initialized:
            raise RuntimeError(f"AnalyzerManager não foi inicializado")
        
        try:
            if self.components.get('intention'):
                return self.components['intention'].analyze_intention(query)
            else:
                return {'error': 'IntentionAnalyzer não disponível', 'fallback': True, 'intention': 'unknown', 'confidence': 0.0}
        except Exception as e:
            self.logger.error(f"❌ Erro na análise de intenção: {e}")
            return {'error': str(e), 'intention': 'error', 'confidence': 0.0}

    def analyze_semantic(self, query: str) -> Dict[str, Any]:
        """Delega análise semântica para o SemanticAnalyzer"""
        if not self.initialized:
            raise RuntimeError(f"AnalyzerManager não foi inicializado")
        
        try:
            if self.components.get('semantic'):
                return self.components['semantic'].analyze_query(query)
            else:
                return {'error': 'SemanticAnalyzer não disponível', 'fallback': True, 'analysis_type': 'semantic', 'confidence': 0.0}
        except Exception as e:
            self.logger.error(f"❌ Erro na análise semântica: {e}")
            return {'error': str(e), 'analysis_type': 'semantic', 'confidence': 0.0}

    def analyze_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delega análise estrutural para o StructuralAnalyzer"""
        if not self.initialized:
            raise RuntimeError(f"AnalyzerManager não foi inicializado")
        
        try:
            if self.components.get('structural'):
                return self.components['structural'].analyze_structure(data)
            else:
                return {'error': 'StructuralAnalyzer não disponível', 'fallback': True, 'structure_quality': 'unknown'}
        except Exception as e:
            self.logger.error(f"❌ Erro na análise estrutural: {e}")
            return {'error': str(e), 'structure_quality': 'error'}

    def analyze_nlp(self, text: str) -> Dict[str, Any]:
        """
        Delega análise NLP para o NLPEnhancedAnalyzer
        
        Args:
            text: Texto para análise
            
        Returns:
            Dict com análise NLP
        """
        
        if not self.initialized:
            raise RuntimeError(f"AnalyzerManager não foi inicializado")
        
        try:
            if self.components.get('nlpenhanced'):
                return self.components['nlpenhanced'].analyze_text(text)
            else:
                return {
                    'error': 'NLPEnhancedAnalyzer não disponível',
                    'fallback': True,
                    'tokens': text.split(),
                    'word_count': len(text.split())
                }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise NLP: {e}")
            return {
                'error': str(e),
                'tokens': [],
                'word_count': 0
            }

    def analyze_metacognitive(self, query: str, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delega análise metacognitiva para o MetacognitiveAnalyzer
        
        Args:
            query: Consulta original
            response: Resposta gerada
            context: Contexto da análise
            
        Returns:
            Dict com análise metacognitiva
        """
        
        if not self.initialized:
            raise RuntimeError(f"AnalyzerManager não foi inicializado")
        
        try:
            if self.components.get('metacognitive'):
                return self.components['metacognitive'].analyze_own_performance(query, response, context)
            else:
                return {
                    'error': 'MetacognitiveAnalyzer não disponível',
                    'fallback': True,
                    'confidence_score': 0.5,
                    'improvement_suggestions': []
                }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise metacognitiva: {e}")
            return {
                'error': str(e),
                'confidence_score': 0.0,
                'improvement_suggestions': []
            }

    def get_best_analyzer(self, query: str, task_type: str = 'general') -> str:
        """
        Determina o melhor analyzer para uma tarefa específica
        
        Args:
            query: Consulta do usuário
            task_type: Tipo de tarefa ('general', 'nlp', 'intention', 'structural')
            
        Returns:
            Nome do melhor analyzer
        """
        
        if not self.initialized:
            raise RuntimeError(f"AnalyzerManager não foi inicializado")
        
        try:
            # Lógica inteligente para escolher o melhor analyzer
            query_lower = query.lower()
            
            # Casos específicos primeiro
            if task_type == 'nlp' or any(word in query_lower for word in ['texto', 'linguagem', 'palavras']):
                if self.components.get('nlpenhanced'):
                    return 'nlpenhanced'
            
            elif task_type == 'intention' or any(word in query_lower for word in ['intenção', 'objetivo', 'quero']):
                if self.components.get('intention'):
                    return 'intention'
            
            elif task_type == 'structural' or any(word in query_lower for word in ['estrutura', 'validar', 'consistência']):
                if self.components.get('structural'):
                    return 'structural'
            
            # Análise automática baseada na complexidade
            word_count = len(query.split())
            
            if word_count > 20:  # Consulta muito complexa
                if self.components.get('nlpenhanced'):
                    return 'nlpenhanced'
                elif self.components.get('metacognitive'):
                    return 'metacognitive'
            
            elif word_count > 10:  # Consulta média
                if self.components.get('query'):
                    return 'query'
                elif self.components.get('intention'):
                    return 'intention'
            
            else:  # Consulta simples
                if self.components.get('intention'):
                    return 'intention'
                elif self.components.get('query'):
                    return 'query'
            
            # Fallback: primeiro analyzer disponível
            for name, component in self.components.items():
                if component is not None:
                    return name
            
            return 'none'
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao escolher melhor analyzer: {e}")
            return 'error'
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do manager"""
        
        return {
            'manager': 'AnalyzerManager',
            'initialized': self.initialized,
            'components': list(self.components.keys()),
            'total_components': len(self.components),
            'function': 'Coordenar múltiplos analyzers (NLP, intenção, contexto)'
        }
    
    def health_check(self) -> bool:
        """Verifica se o manager está funcionando"""
        
        if not self.initialized:
            return False
        
        # Verificar se todos os componentes estão funcionais
        for name, component in self.components.items():
            if component is None:
                self.logger.warning(f"Componente {name} não está disponível")
                return False
        
        return True
    
    def __str__(self) -> str:
        return f"AnalyzerManager(components={len(self.components)})"
    
    def __repr__(self) -> str:
        return f"AnalyzerManager(initialized={self.initialized})"

# Instância global do manager
analyzermanager_instance = None

def get_analyzermanager() -> AnalyzerManager:
    """Retorna instância singleton do AnalyzerManager"""
    
    global analyzermanager_instance
    
    if analyzermanager_instance is None:
        analyzermanager_instance = AnalyzerManager()
    
    return analyzermanager_instance

# Função de conveniência para compatibilidade
def get_manager() -> AnalyzerManager:
    """Alias para get_analyzermanager()"""
    return get_analyzermanager()

# Função para compatibilidade com imports antigos
def get_analyzer_manager(orchestrator=None) -> AnalyzerManager:
    """Retorna instância do AnalyzerManager (compatibilidade)"""
    manager = get_analyzermanager()
    if orchestrator and hasattr(manager, 'initialize_diagnostics_analyzer'):
        manager.initialize_diagnostics_analyzer(orchestrator)
    return manager

if __name__ == "__main__":
    # Teste básico
    manager = get_analyzermanager()
    print(f"Manager: {manager}")
    print(f"Status: {manager.get_status()}")
    print(f"Health: {manager.health_check()}")