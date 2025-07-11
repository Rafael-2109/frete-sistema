"""
🧠 INTELLIGENCE COORDINATOR - Coordenador de Inteligência
========================================================

Módulo responsável por coordenar todos os componentes de inteligência artificial do sistema.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class IntelligenceCoordinator:
    """
    Coordenador central de inteligência artificial.
    
    Responsabilidades:
    - Coordenar múltiplos sistemas de IA
    - Orquestrar processamento inteligente
    - Gerenciar pipeline de análise
    - Sincronizar resultados de IA
    - Otimizar performance de IA
    """
    
    def __init__(self):
        """Inicializa o coordenador de inteligência."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("🧠 IntelligenceCoordinator inicializado")
        
        # Configurações do coordenador
        self.config = {
            'max_concurrent_operations': 5,
            'operation_timeout_seconds': 300,
            'retry_attempts': 3,
            'fallback_enabled': True,
            'parallel_processing': True,
            'intelligence_threshold': 0.6
        }
        
        # Componentes de IA registrados
        self.ai_components = {}
        
        # Pipeline de processamento
        self.processing_pipeline = []
        
        # Cache de resultados de IA
        self.ai_cache = {}
        
        # Métricas de coordenação
        self.coordination_metrics = {
            'operations_coordinated': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_processing_time': 0.0,
            'cache_hit_rate': 0.0,
            'components_active': 0
        }
        
        # Pool de threads para processamento paralelo
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config['max_concurrent_operations'])
        
        # Estado de coordenação
        self.coordination_state = {
            'active_operations': {},
            'queued_operations': [],
            'completed_operations': [],
            'failed_operations': []
        }
        
        # Inicializar componentes
        self._initialize_ai_components()
    
    def coordinate_intelligence_operation(self, operation_type: str, data: Any, priority: str = 'normal', **kwargs) -> Dict[str, Any]:
        """
        Coordena uma operação de inteligência.
        
        Args:
            operation_type: Tipo de operação ('analysis', 'synthesis', 'prediction', 'optimization')
            data: Dados para processamento
            priority: Prioridade da operação ('low', 'normal', 'high', 'critical')
            **kwargs: Parâmetros adicionais
            
        Returns:
            Resultado coordenado da operação de IA
        """
        try:
            operation_id = f"op_{datetime.now().timestamp()}"
            
            result = {
                'operation_id': operation_id,
                'timestamp': datetime.now().isoformat(),
                'operation_type': operation_type,
                'priority': priority,
                'status': 'success',
                'intelligence_results': {},
                'coordination_info': {},
                'performance_metrics': {}
            }
            
            # Registrar operação
            self._register_operation(operation_id, operation_type, priority, data)
            
            # Verificar cache primeiro
            cache_key = self._generate_cache_key(operation_type, data, kwargs)
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                result.update(cached_result)
                result['source'] = 'cache'
                self.coordination_metrics['cache_hit_rate'] += 1
                return result
            
            # Determinar estratégia de processamento
            processing_strategy = self._determine_processing_strategy(operation_type, priority, data)
            result['coordination_info']['strategy'] = processing_strategy
            
            # Executar operação baseada na estratégia
            start_time = datetime.now()
            
            if processing_strategy == 'parallel':
                intelligence_results = self._execute_parallel_intelligence(operation_type, data, **kwargs)
            elif processing_strategy == 'sequential':
                intelligence_results = self._execute_sequential_intelligence(operation_type, data, **kwargs)
            elif processing_strategy == 'hybrid':
                intelligence_results = self._execute_hybrid_intelligence(operation_type, data, **kwargs)
            else:
                intelligence_results = self._execute_single_intelligence(operation_type, data, **kwargs)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Consolidar resultados
            consolidated_results = self._consolidate_intelligence_results(intelligence_results, operation_type)
            result['intelligence_results'] = consolidated_results
            
            # Calcular métricas de performance
            performance_metrics = self._calculate_performance_metrics(intelligence_results, processing_time)
            result['performance_metrics'] = performance_metrics
            
            # Validar qualidade dos resultados
            quality_score = self._validate_intelligence_quality(consolidated_results)
            result['quality_score'] = quality_score
            
            # Cachear resultado se qualidade boa
            if quality_score >= self.config['intelligence_threshold']:
                self._cache_result(cache_key, result)
            
            # Atualizar métricas
            self._update_coordination_metrics('success', processing_time)
            
            # Completar operação
            self._complete_operation(operation_id, result)
            
            self.logger.info(f"✅ Operação de IA coordenada: {operation_type}, qualidade: {quality_score:.2f}, tempo: {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro na coordenação de IA: {e}")
            self._update_coordination_metrics('failure', 0)
            
            return {
                'operation_id': operation_id,
                'timestamp': datetime.now().isoformat(),
                'operation_type': operation_type,
                'status': 'error',
                'error': str(e),
                'fallback_attempted': self._attempt_fallback(operation_type, data, **kwargs)
            }
    
    def coordinate_multi_ai_synthesis(self, ai_requests: List[Dict[str, Any]], synthesis_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Coordena síntese de múltiplas requisições de IA.
        
        Args:
            ai_requests: Lista de requisições para diferentes AIs
            synthesis_type: Tipo de síntese ('comprehensive', 'consensus', 'best_result')
            
        Returns:
            Resultado sintetizado de múltiplos AIs
        """
        try:
            synthesis_result = {
                'timestamp': datetime.now().isoformat(),
                'synthesis_type': synthesis_type,
                'requests_count': len(ai_requests),
                'status': 'success',
                'individual_results': [],
                'synthesized_intelligence': {},
                'confidence_matrix': {},
                'consensus_analysis': {}
            }
            
            # Processar cada requisição de IA
            individual_results = []
            
            if self.config['parallel_processing']:
                # Processamento paralelo
                futures = []
                for i, request in enumerate(ai_requests):
                    future = self.thread_pool.submit(
                        self._process_ai_request, 
                        request, 
                        f"request_{i}"
                    )
                    futures.append(future)
                
                # Coletar resultados
                for future in as_completed(futures, timeout=self.config['operation_timeout_seconds']):
                    try:
                        result = future.result()
                        individual_results.append(result)
                    except Exception as e:
                        self.logger.warning(f"⚠️ Falha em requisição de IA: {e}")
            else:
                # Processamento sequencial
                for i, request in enumerate(ai_requests):
                    try:
                        result = self._process_ai_request(request, f"request_{i}")
                        individual_results.append(result)
                    except Exception as e:
                        self.logger.warning(f"⚠️ Falha em requisição {i}: {e}")
            
            synthesis_result['individual_results'] = individual_results
            
            # Realizar síntese baseada no tipo
            if synthesis_type == 'comprehensive':
                synthesized_intelligence = self._comprehensive_synthesis(individual_results)
            elif synthesis_type == 'consensus':
                synthesized_intelligence = self._consensus_synthesis(individual_results)
            elif synthesis_type == 'best_result':
                synthesized_intelligence = self._best_result_synthesis(individual_results)
            else:
                synthesized_intelligence = self._default_synthesis(individual_results)
            
            synthesis_result['synthesized_intelligence'] = synthesized_intelligence
            
            # Calcular matriz de confiança
            confidence_matrix = self._calculate_confidence_matrix(individual_results)
            synthesis_result['confidence_matrix'] = confidence_matrix
            
            # Análise de consenso
            consensus_analysis = self._analyze_consensus(individual_results)
            synthesis_result['consensus_analysis'] = consensus_analysis
            
            self.logger.info(f"✅ Síntese multi-IA concluída: {len(individual_results)} resultados, tipo: {synthesis_type}")
            
            return synthesis_result
            
        except Exception as e:
            self.logger.error(f"❌ Erro na síntese multi-IA: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'synthesis_type': synthesis_type,
                'status': 'error',
                'error': str(e)
            }
    
    def optimize_intelligence_pipeline(self) -> Dict[str, Any]:
        """
        Otimiza o pipeline de inteligência.
        
        Returns:
            Relatório de otimização
        """
        try:
            optimization_report = {
                'timestamp': datetime.now().isoformat(),
                'optimizations_applied': [],
                'performance_improvements': {},
                'component_adjustments': {},
                'pipeline_changes': {}
            }
            
            # Analisar performance atual
            current_performance = self._analyze_current_performance()
            
            # Otimizar componentes de IA
            component_optimizations = self._optimize_ai_components()
            optimization_report['component_adjustments'] = component_optimizations
            
            # Otimizar pipeline
            pipeline_optimizations = self._optimize_processing_pipeline()
            optimization_report['pipeline_changes'] = pipeline_optimizations
            
            # Otimizar cache
            cache_optimizations = self._optimize_ai_cache()
            optimization_report['cache_optimizations'] = cache_optimizations
            
            # Ajustar configurações
            config_adjustments = self._adjust_intelligence_config()
            optimization_report['config_adjustments'] = config_adjustments
            
            # Calcular melhorias
            new_performance = self._analyze_current_performance()
            performance_improvements = self._calculate_performance_improvements(
                current_performance, new_performance
            )
            optimization_report['performance_improvements'] = performance_improvements
            
            self.logger.info("🔧 Otimização do pipeline de IA concluída")
            
            return optimization_report
            
        except Exception as e:
            self.logger.error(f"❌ Erro na otimização: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    def register_ai_component(self, component_name: str, component_instance: Any, capabilities: List[str], priority: int = 5) -> bool:
        """
        Registra um componente de IA.
        
        Args:
            component_name: Nome do componente
            component_instance: Instância do componente
            capabilities: Lista de capacidades
            priority: Prioridade do componente
            
        Returns:
            True se registrado com sucesso
        """
        try:
            self.ai_components[component_name] = {
                'instance': component_instance,
                'capabilities': capabilities,
                'priority': priority,
                'registered_at': datetime.now().isoformat(),
                'usage_count': 0,
                'success_rate': 1.0,
                'average_response_time': 0.0,
                'last_used': None
            }
            
            self.coordination_metrics['components_active'] = len(self.ai_components)
            
            self.logger.info(f"✅ Componente de IA registrado: {component_name} com {len(capabilities)} capacidades")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar componente '{component_name}': {e}")
            return False
    
    def get_intelligence_status(self) -> Dict[str, Any]:
        """
        Obtém status do sistema de coordenação de inteligência.
        
        Returns:
            Status detalhado
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'active_components': len(self.ai_components),
            'active_operations': len(self.coordination_state['active_operations']),
            'queued_operations': len(self.coordination_state['queued_operations']),
            'coordination_metrics': self.coordination_metrics.copy(),
            'config': self.config.copy(),
            'pipeline_size': len(self.processing_pipeline),
            'cache_size': len(self.ai_cache)
        }
    
    def _initialize_ai_components(self):
        """Inicializa componentes de IA."""
        try:
            # Tentar carregar analyzers
            from ..analyzers import get_analyzer_manager
            analyzer_manager = get_analyzer_manager()
            if analyzer_manager:
                self.register_ai_component(
                    'analyzer_manager',
                    analyzer_manager,
                    ['analysis', 'intention', 'structure', 'semantic'],
                    priority=9
                )
            
            # Tentar carregar processors
            from ..processors import get_intelligence_processor
            intelligence_processor = get_intelligence_processor()
            if intelligence_processor:
                self.register_ai_component(
                    'intelligence_processor',
                    intelligence_processor,
                    ['insights', 'patterns', 'decisions', 'synthesis'],
                    priority=8
                )
            
            # Tentar carregar learning systems
            from ..learners import get_adaptive_learning
            adaptive_learning = get_adaptive_learning()
            if adaptive_learning:
                self.register_ai_component(
                    'adaptive_learning',
                    adaptive_learning,
                    ['learning', 'adaptation', 'optimization'],
                    priority=7
                )
                
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao inicializar componentes de IA: {e}")
    
    def _determine_processing_strategy(self, operation_type: str, priority: str, data: Any) -> str:
        """Determina estratégia de processamento."""
        # Estratégia baseada no tipo e prioridade
        if priority == 'critical':
            return 'parallel'
        elif operation_type in ['synthesis', 'complex_analysis']:
            return 'hybrid'
        elif len(self.ai_components) > 3:
            return 'parallel'
        else:
            return 'sequential'
    
    def _execute_parallel_intelligence(self, operation_type: str, data: Any, **kwargs) -> List[Dict[str, Any]]:
        """Executa processamento paralelo de IA."""
        results = []
        futures = []
        
        # Executar em todos os componentes relevantes
        for component_name, component_info in self.ai_components.items():
            if self._component_supports_operation(component_info, operation_type):
                future = self.thread_pool.submit(
                    self._execute_component_operation,
                    component_name,
                    component_info,
                    operation_type,
                    data,
                    **kwargs
                )
                futures.append((component_name, future))
        
        # Coletar resultados
        for component_name, future in futures:
            try:
                result = future.result(timeout=self.config['operation_timeout_seconds'])
                result['component'] = component_name
                results.append(result)
            except Exception as e:
                self.logger.warning(f"⚠️ Falha no componente {component_name}: {e}")
        
        return results
    
    def _execute_sequential_intelligence(self, operation_type: str, data: Any, **kwargs) -> List[Dict[str, Any]]:
        """Executa processamento sequencial de IA."""
        results = []
        
        # Ordenar componentes por prioridade
        sorted_components = sorted(
            self.ai_components.items(),
            key=lambda x: x[1]['priority'],
            reverse=True
        )
        
        for component_name, component_info in sorted_components:
            if self._component_supports_operation(component_info, operation_type):
                try:
                    result = self._execute_component_operation(
                        component_name, component_info, operation_type, data, **kwargs
                    )
                    result['component'] = component_name
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"⚠️ Falha no componente {component_name}: {e}")
        
        return results
    
    def _execute_hybrid_intelligence(self, operation_type: str, data: Any, **kwargs) -> List[Dict[str, Any]]:
        """Executa processamento híbrido de IA."""
        # Combinar estratégias baseado na situação
        high_priority_components = [
            (name, info) for name, info in self.ai_components.items()
            if info['priority'] >= 8 and self._component_supports_operation(info, operation_type)
        ]
        
        other_components = [
            (name, info) for name, info in self.ai_components.items()
            if info['priority'] < 8 and self._component_supports_operation(info, operation_type)
        ]
        
        results = []
        
        # Executar componentes prioritários sequencialmente
        for component_name, component_info in high_priority_components:
            try:
                result = self._execute_component_operation(
                    component_name, component_info, operation_type, data, **kwargs
                )
                result['component'] = component_name
                result['execution_type'] = 'sequential_priority'
                results.append(result)
            except Exception as e:
                self.logger.warning(f"⚠️ Falha no componente prioritário {component_name}: {e}")
        
        # Executar outros componentes em paralelo
        if other_components:
            futures = []
            for component_name, component_info in other_components:
                future = self.thread_pool.submit(
                    self._execute_component_operation,
                    component_name, component_info, operation_type, data, **kwargs
                )
                futures.append((component_name, future))
            
            for component_name, future in futures:
                try:
                    result = future.result(timeout=self.config['operation_timeout_seconds'])
                    result['component'] = component_name
                    result['execution_type'] = 'parallel_secondary'
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"⚠️ Falha no componente {component_name}: {e}")
        
        return results
    
    def _execute_single_intelligence(self, operation_type: str, data: Any, **kwargs) -> List[Dict[str, Any]]:
        """Executa processamento em componente único."""
        # Escolher melhor componente para a operação
        best_component = self._select_best_component(operation_type)
        
        if best_component:
            component_name, component_info = best_component
            try:
                result = self._execute_component_operation(
                    component_name, component_info, operation_type, data, **kwargs
                )
                result['component'] = component_name
                return [result]
            except Exception as e:
                self.logger.error(f"❌ Falha no componente único {component_name}: {e}")
        
        return []
    
    def _execute_component_operation(self, component_name: str, component_info: Dict[str, Any], operation_type: str, data: Any, **kwargs) -> Dict[str, Any]:
        """Executa operação em um componente específico."""
        start_time = datetime.now()
        component_instance = component_info['instance']
        
        try:
            # Tentar diferentes métodos baseado no tipo de operação
            if operation_type == 'analysis' and hasattr(component_instance, 'analyze'):
                result = component_instance.analyze(data, **kwargs)
            elif operation_type == 'synthesis' and hasattr(component_instance, 'synthesize'):
                result = component_instance.synthesize(data, **kwargs)
            elif operation_type == 'prediction' and hasattr(component_instance, 'predict'):
                result = component_instance.predict(data, **kwargs)
            elif operation_type == 'optimization' and hasattr(component_instance, 'optimize'):
                result = component_instance.optimize(data, **kwargs)
            elif hasattr(component_instance, 'process'):
                result = component_instance.process(data, operation_type, **kwargs)
            elif hasattr(component_instance, 'process_intelligence'):
                result = component_instance.process_intelligence(data, operation_type, **kwargs)
            else:
                # Fallback genérico
                result = {
                    'status': 'unsupported',
                    'message': f'Operação {operation_type} não suportada por {component_name}'
                }
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Atualizar estatísticas do componente
            self._update_component_stats(component_name, processing_time, True)
            
            # Enriquecer resultado
            if isinstance(result, dict):
                result['processing_time'] = str(processing_time)
                result['component'] = component_name
                result['timestamp'] = end_time.isoformat()
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Atualizar estatísticas do componente
            self._update_component_stats(component_name, processing_time, False)
            
            raise e
    
    def _component_supports_operation(self, component_info: Dict[str, Any], operation_type: str) -> bool:
        """Verifica se componente suporta operação."""
        capabilities = component_info.get('capabilities', [])
        
        # Mapeamento de operações para capacidades
        operation_mapping = {
            'analysis': ['analysis', 'analyze', 'intention', 'structure', 'semantic'],
            'synthesis': ['synthesis', 'insights', 'patterns'],
            'prediction': ['prediction', 'forecast', 'learning'],
            'optimization': ['optimization', 'learning', 'adaptation']
        }
        
        required_capabilities = operation_mapping.get(operation_type, [operation_type])
        
        return any(cap in capabilities for cap in required_capabilities)
    
    def _select_best_component(self, operation_type: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Seleciona melhor componente para operação."""
        suitable_components = [
            (name, info) for name, info in self.ai_components.items()
            if self._component_supports_operation(info, operation_type)
        ]
        
        if not suitable_components:
            return None
        
        # Ordenar por prioridade e taxa de sucesso
        suitable_components.sort(
            key=lambda x: (x[1]['priority'], x[1]['success_rate']),
            reverse=True
        )
        
        return suitable_components[0]
    
    def _consolidate_intelligence_results(self, results: List[Dict[str, Any]], operation_type: str) -> Dict[str, Any]:
        """Consolida resultados de múltiplos componentes."""
        if not results:
            return {'status': 'no_results', 'components_used': 0}
        
        consolidated = {
            'operation_type': operation_type,
            'components_used': len(results),
            'timestamp': datetime.now().isoformat(),
            'results_by_component': {},
            'consensus_results': {},
            'best_result': None,
            'confidence_scores': {}
        }
        
        # Organizar resultados por componente
        for result in results:
            component = result.get('component', 'unknown')
            consolidated['results_by_component'][component] = result
            
            # Extrair score de confiança se disponível
            confidence = result.get('confidence_score', result.get('confidence', 0.5))
            consolidated['confidence_scores'][component] = confidence
        
        # Encontrar melhor resultado
        if consolidated['confidence_scores']:
            best_component = max(consolidated['confidence_scores'], key=consolidated['confidence_scores'].get)
            consolidated['best_result'] = consolidated['results_by_component'][best_component]
        
        # Criar resultado consensual simples
        consolidated['consensus_results'] = self._create_simple_consensus(results)
        
        return consolidated
    
    def _create_simple_consensus(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cria consenso simples dos resultados."""
        if not results:
            return {}
        
        consensus = {
            'average_confidence': 0.0,
            'common_insights': [],
            'aggregated_data': {}
        }
        
        # Calcular confiança média
        confidences = []
        for result in results:
            confidence = result.get('confidence_score', result.get('confidence', 0.5))
            confidences.append(confidence)
        
        if confidences:
            consensus['average_confidence'] = sum(confidences) / len(confidences)
        
        # Agregar insights comuns (simplificado)
        all_insights = []
        for result in results:
            if 'insights' in result:
                all_insights.extend(result['insights'])
            elif 'intelligence_output' in result and 'data_insights' in result['intelligence_output']:
                all_insights.extend(result['intelligence_output']['data_insights'])
        
        # Manter insights únicos
        consensus['common_insights'] = list(set(all_insights))
        
        return consensus
    
    # Métodos auxiliares (implementação básica)
    def _register_operation(self, operation_id: str, operation_type: str, priority: str, data: Any):
        """Registra operação no estado."""
        self.coordination_state['active_operations'][operation_id] = {
            'type': operation_type,
            'priority': priority,
            'started_at': datetime.now().isoformat(),
            'data_size': len(str(data))
        }
    
    def _complete_operation(self, operation_id: str, result: Dict[str, Any]):
        """Completa operação."""
        if operation_id in self.coordination_state['active_operations']:
            operation_info = self.coordination_state['active_operations'].pop(operation_id)
            operation_info['completed_at'] = datetime.now().isoformat()
            operation_info['result_status'] = result.get('status', 'unknown')
            self.coordination_state['completed_operations'].append(operation_info)
    
    def _generate_cache_key(self, operation_type: str, data: Any, kwargs: Dict[str, Any]) -> str:
        """Gera chave de cache."""
        import hashlib
        content = f"{operation_type}|{str(data)}|{str(sorted(kwargs.items()))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Obtém resultado do cache."""
        if cache_key in self.ai_cache:
            cache_entry = self.ai_cache[cache_key]
            # Verificar TTL (30 minutos)
            cached_at = datetime.fromisoformat(cache_entry['cached_at'])
            if datetime.now() - cached_at < timedelta(minutes=30):
                return cache_entry['result']
            else:
                del self.ai_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Armazena resultado no cache."""
        self.ai_cache[cache_key] = {
            'result': result,
            'cached_at': datetime.now().isoformat()
        }
    
    def _calculate_performance_metrics(self, results: List[Dict[str, Any]], processing_time: float) -> Dict[str, Any]:
        """Calcula métricas de performance."""
        return {
            'total_processing_time': processing_time,
            'components_used': len(results),
            'average_confidence': sum(r.get('confidence_score', 0.5) for r in results) / len(results) if results else 0.0,
            'success_rate': len([r for r in results if r.get('status') == 'success']) / len(results) if results else 0.0
        }
    
    def _validate_intelligence_quality(self, results: Dict[str, Any]) -> float:
        """Valida qualidade da inteligência."""
        base_score = 0.5
        
        # Aumentar score baseado em fatores
        if results.get('components_used', 0) > 1:
            base_score += 0.2
        
        if results.get('consensus_results', {}).get('average_confidence', 0) > 0.7:
            base_score += 0.2
        
        if results.get('best_result', {}).get('confidence_score', 0) > 0.8:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _update_coordination_metrics(self, status: str, processing_time: float):
        """Atualiza métricas de coordenação."""
        self.coordination_metrics['operations_coordinated'] += 1
        
        if status == 'success':
            self.coordination_metrics['successful_operations'] += 1
        else:
            self.coordination_metrics['failed_operations'] += 1
        
        # Atualizar tempo médio de processamento
        total_ops = self.coordination_metrics['operations_coordinated']
        current_avg = self.coordination_metrics['average_processing_time']
        self.coordination_metrics['average_processing_time'] = (current_avg * (total_ops - 1) + processing_time) / total_ops
    
    def _update_component_stats(self, component_name: str, processing_time: float, success: bool):
        """Atualiza estatísticas do componente."""
        if component_name in self.ai_components:
            component_info = self.ai_components[component_name]
            component_info['usage_count'] += 1
            component_info['last_used'] = datetime.now().isoformat()
            
            # Atualizar taxa de sucesso
            usage_count = component_info['usage_count']
            current_rate = component_info['success_rate']
            if success:
                component_info['success_rate'] = (current_rate * (usage_count - 1) + 1) / usage_count
            else:
                component_info['success_rate'] = (current_rate * (usage_count - 1)) / usage_count
            
            # Atualizar tempo médio de resposta
            current_avg_time = component_info['average_response_time']
            component_info['average_response_time'] = (current_avg_time * (usage_count - 1) + processing_time) / usage_count
    
    def _attempt_fallback(self, operation_type: str, data: Any, **kwargs) -> bool:
        """Tenta fallback em caso de erro."""
        if not self.config['fallback_enabled']:
            return False
        
        try:
            # Fallback simples - usar componente de maior prioridade
            best_component = self._select_best_component(operation_type)
            if best_component:
                component_name, component_info = best_component
                result = self._execute_component_operation(component_name, component_info, operation_type, data, **kwargs)
                return result.get('status') == 'success'
        except Exception:
            pass
        
        return False
    
    # Métodos auxiliares para síntese (implementação básica)
    def _process_ai_request(self, request: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Processa uma requisição de IA."""
        operation_type = request.get('type', 'analysis')
        data = request.get('data', {})
        kwargs = request.get('params', {})
        
        return self.coordinate_intelligence_operation(operation_type, data, **kwargs)
    
    def _comprehensive_synthesis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Síntese abrangente."""
        return {
            'synthesis_type': 'comprehensive',
            'total_results': len(results),
            'combined_insights': self._combine_all_insights(results),
            'overall_confidence': self._calculate_overall_confidence(results)
        }
    
    def _consensus_synthesis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Síntese por consenso."""
        return {
            'synthesis_type': 'consensus',
            'consensus_points': self._find_consensus_points(results),
            'agreement_level': self._calculate_agreement_level(results)
        }
    
    def _best_result_synthesis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Síntese do melhor resultado."""
        if not results:
            return {}
        
        best_result = max(results, key=lambda x: x.get('quality_score', 0))
        return {
            'synthesis_type': 'best_result',
            'best_result': best_result,
            'selection_criteria': 'highest_quality_score'
        }
    
    def _default_synthesis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Síntese padrão."""
        return {
            'synthesis_type': 'default',
            'results_count': len(results),
            'summary': 'Síntese básica de resultados múltiplos'
        }
    
    # Métodos auxiliares adicionais (implementação básica)
    def _combine_all_insights(self, results: List[Dict[str, Any]]) -> List[str]:
        """Combina todos os insights."""
        all_insights = []
        for result in results:
            insights = result.get('intelligence_results', {}).get('consensus_results', {}).get('common_insights', [])
            all_insights.extend(insights)
        return list(set(all_insights))
    
    def _calculate_overall_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calcula confiança geral."""
        confidences = [r.get('quality_score', 0.5) for r in results]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _find_consensus_points(self, results: List[Dict[str, Any]]) -> List[str]:
        """Encontra pontos de consenso."""
        return ["Consenso detectado entre resultados"]  # Placeholder
    
    def _calculate_agreement_level(self, results: List[Dict[str, Any]]) -> float:
        """Calcula nível de concordância."""
        return 0.7  # Placeholder
    
    def _calculate_confidence_matrix(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calcula matriz de confiança."""
        matrix = {}
        for i, result in enumerate(results):
            matrix[f"result_{i}"] = result.get('quality_score', 0.5)
        return matrix
    
    def _analyze_consensus(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analisa consenso."""
        return {
            'consensus_found': len(results) > 1,
            'consensus_strength': self._calculate_agreement_level(results),
            'divergent_points': []
        }
    
    # Métodos de otimização (implementação básica)
    def _analyze_current_performance(self) -> Dict[str, Any]:
        """Analisa performance atual."""
        return self.coordination_metrics.copy()
    
    def _optimize_ai_components(self) -> Dict[str, Any]:
        """Otimiza componentes de IA."""
        return {'components_optimized': len(self.ai_components)}
    
    def _optimize_processing_pipeline(self) -> Dict[str, Any]:
        """Otimiza pipeline de processamento."""
        return {'pipeline_optimized': True}
    
    def _optimize_ai_cache(self) -> Dict[str, Any]:
        """Otimiza cache de IA."""
        # Limpar cache antigo
        old_size = len(self.ai_cache)
        current_time = datetime.now()
        
        expired_keys = []
        for key, entry in self.ai_cache.items():
            cached_at = datetime.fromisoformat(entry['cached_at'])
            if current_time - cached_at > timedelta(minutes=30):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.ai_cache[key]
        
        return {
            'cache_size_before': old_size,
            'cache_size_after': len(self.ai_cache),
            'entries_removed': len(expired_keys)
        }
    
    def _adjust_intelligence_config(self) -> Dict[str, Any]:
        """Ajusta configurações de inteligência."""
        adjustments = {}
        
        # Ajustar baseado em métricas
        success_rate = self.coordination_metrics['successful_operations'] / max(self.coordination_metrics['operations_coordinated'], 1)
        
        if success_rate < 0.7:
            # Diminuir threshold de inteligência
            old_threshold = self.config['intelligence_threshold']
            self.config['intelligence_threshold'] = max(old_threshold - 0.1, 0.3)
            adjustments['intelligence_threshold'] = f"reduced from {old_threshold} to {self.config['intelligence_threshold']}"
        
        return adjustments
    
    def _calculate_performance_improvements(self, old_performance: Dict[str, Any], new_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula melhorias de performance."""
        improvements = {}
        
        for key in ['successful_operations', 'average_processing_time']:
            if key in old_performance and key in new_performance:
                old_val = old_performance[key]
                new_val = new_performance[key]
                if old_val > 0:
                    improvement = ((new_val - old_val) / old_val) * 100
                    improvements[key] = f"{improvement:.1f}%"
        
        return improvements


def get_intelligence_coordinator() -> IntelligenceCoordinator:
    """
    Obtém instância do coordenador de inteligência.
    
    Returns:
        Instância do IntelligenceCoordinator
    """
    return IntelligenceCoordinator() 