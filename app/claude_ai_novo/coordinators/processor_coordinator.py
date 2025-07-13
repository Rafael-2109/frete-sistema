#!/usr/bin/env python3
"""
ProcessorCoordinator - Coordenação entre processadores
Extraído do processor_manager.py para melhor organização
"""

from app.claude_ai_novo.processors.base import BaseProcessor, logging, datetime
from app.claude_ai_novo.utils.processor_registry import get_processor_registry
from typing import Dict, Any, Optional, List, Callable
import asyncio

class ProcessorCoordinator(BaseProcessor):
    """Coordena execução entre múltiplos processadores"""
    
    def __init__(self):
        super().__init__()
        self.registry = get_processor_registry()
        self.execution_history = []
        self.active_chains = {}
        
    def execute_processor_chain(self, chain_config: List[Dict[str, Any]], 
                               initial_data: Any = None) -> Dict[str, Any]:
        """Executa uma cadeia de processadores"""
        
        chain_id = f"chain_{datetime.now().timestamp()}"
        self.active_chains[chain_id] = {
            'config': chain_config,
            'started_at': datetime.now(),
            'status': 'running',
            'results': []
        }
        
        try:
            self._log_operation(f"execute_processor_chain", f"chain_id: {chain_id}")
            
            current_data = initial_data
            results = []
            
            for step_idx, step_config in enumerate(chain_config):
                step_result = self._execute_chain_step(step_config, current_data, step_idx)
                results.append(step_result)
                
                # Usar resultado como entrada para próximo step
                current_data = step_result.get('output', current_data)
                
                # Verificar se deve parar
                if step_result.get('stop_chain', False):
                    self.logger.info(f"Cadeia {chain_id} interrompida no step {step_idx}")
                    break
            
            # Marcar como completa
            self.active_chains[chain_id]['status'] = 'completed'
            self.active_chains[chain_id]['results'] = results
            self.active_chains[chain_id]['completed_at'] = datetime.now()
            
            return {
                'chain_id': chain_id,
                'success': True,
                'results': results,
                'final_output': current_data,
                'execution_time': (datetime.now() - self.active_chains[chain_id]['started_at']).total_seconds()
            }
            
        except Exception as e:
            self.active_chains[chain_id]['status'] = 'failed'
            self.active_chains[chain_id]['error'] = str(e)
            
            error_msg = self._handle_error(e, f"execute_processor_chain")
            return {
                'chain_id': chain_id,
                'success': False,
                'error': error_msg,
                'execution_time': (datetime.now() - self.active_chains[chain_id]['started_at']).total_seconds()
            }
    
    def _execute_chain_step(self, step_config: Dict[str, Any], 
                           input_data: Any, step_idx: int) -> Dict[str, Any]:
        """Executa um step individual da cadeia"""
        
        processor_name = step_config.get('processor')
        method_name = step_config.get('method', 'process')
        step_params = step_config.get('params', {})
        
        if not processor_name:
            raise ValueError(f"Step {step_idx}: Nome do processador não especificado")
        
        # Obter processador
        processor = self.registry.get_processor(processor_name)
        if processor is None:
            raise ValueError(f"Step {step_idx}: Processador '{processor_name}' não encontrado")
        
        try:
            # Preparar argumentos
            args = [input_data] if input_data is not None else []
            
            # Executar método
            if hasattr(processor, method_name):
                method = getattr(processor, method_name)
                
                # NOVO: Tratamento especial para métodos conhecidos que precisam de argumentos separados
                if method_name == 'carregar_contexto_inteligente' and isinstance(input_data, dict):
                    # Desempacotar argumentos para ContextProcessor
                    consulta = input_data.get('consulta', '')
                    analise = input_data.get('analise', {})
                    if asyncio.iscoroutinefunction(method):
                        result = asyncio.run(method(consulta, analise))
                    else:
                        result = method(consulta, analise)
                        
                elif method_name == 'process_query' and isinstance(input_data, dict):
                    # Desempacotar argumentos para QueryProcessor
                    consulta = input_data.get('consulta', '')
                    user_context = input_data.get('user_context', input_data.get('context', {}))
                    if asyncio.iscoroutinefunction(method):
                        result = asyncio.run(method(consulta, user_context))
                    else:
                        result = method(consulta, user_context)
                        
                elif method_name == 'gerar_resposta_otimizada' and isinstance(input_data, dict):
                    # Desempacotar argumentos para ResponseProcessor
                    consulta = input_data.get('consulta', '')
                    analise = input_data.get('analise', {})
                    user_context = input_data.get('user_context', input_data.get('context', {}))
                    if asyncio.iscoroutinefunction(method):
                        result = asyncio.run(method(consulta, analise, user_context))
                    else:
                        result = method(consulta, analise, user_context)
                        
                else:
                    # Comportamento padrão para outros métodos
                    if asyncio.iscoroutinefunction(method):
                        # Método assíncrono
                        result = asyncio.run(method(*args, **step_params))
                    else:
                        # Método síncrono
                        result = method(*args, **step_params)
                
                return {
                    'step_index': step_idx,
                    'processor': processor_name,
                    'method': method_name,
                    'success': True,
                    'output': result,
                    'execution_time': datetime.now()
                }
                
            else:
                raise AttributeError(f"Método '{method_name}' não encontrado no processador '{processor_name}'")
                
        except Exception as e:
            self.logger.error(f"Erro no step {step_idx}: {e}")
            return {
                'step_index': step_idx,
                'processor': processor_name,
                'method': method_name,
                'success': False,
                'error': str(e),
                'execution_time': datetime.now()
            }
    
    def execute_parallel_processors(self, processor_configs: List[Dict[str, Any]], 
                                   input_data: Any = None) -> Dict[str, Any]:
        """Executa múltiplos processadores em paralelo"""
        
        parallel_id = f"parallel_{datetime.now().timestamp()}"
        self._log_operation(f"execute_parallel_processors", f"parallel_id: {parallel_id}")
        
        start_time = datetime.now()
        
        try:
            results = []
            
            # Para cada configuração, executar processador
            for config in processor_configs:
                try:
                    result = self._execute_single_processor(config, input_data)
                    results.append(result)
                except Exception as e:
                    results.append({
                        'processor': config.get('processor', 'unknown'),
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'parallel_id': parallel_id,
                'success': True,
                'results': results,
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'total_processors': len(processor_configs),
                'successful_processors': sum(1 for r in results if r.get('success', False))
            }
            
        except Exception as e:
            error_msg = self._handle_error(e, "execute_parallel_processors")
            return {
                'parallel_id': parallel_id,
                'success': False,
                'error': error_msg,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }
    
    def _execute_single_processor(self, config: Dict[str, Any], input_data: Any) -> Dict[str, Any]:
        """Executa um processador individual"""
        
        processor_name = config.get('processor')
        method_name = config.get('method', 'process')
        params = config.get('params', {})
        
        # Validar se processor_name foi fornecido
        if not processor_name:
            raise ValueError("Nome do processador não especificado na configuração")
        
        processor = self.registry.get_processor(processor_name)
        if processor is None:
            raise ValueError(f"Processador '{processor_name}' não encontrado")
        
        if not hasattr(processor, method_name):
            raise AttributeError(f"Método '{method_name}' não encontrado no processador '{processor_name}'")
        
        method = getattr(processor, method_name)
        
        # Preparar argumentos
        args = [input_data] if input_data is not None else []
        
        # Executar
        if asyncio.iscoroutinefunction(method):
            result = asyncio.run(method(*args, **params))
        else:
            result = method(*args, **params)
        
        return {
            'processor': processor_name,
            'method': method_name,
            'success': True,
            'output': result,
            'execution_time': datetime.now()
        }
    
    def create_processing_pipeline(self, pipeline_name: str, 
                                 steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cria um pipeline de processamento nomeado"""
        
        if pipeline_name in self.active_chains:
            self.logger.warning(f"Pipeline '{pipeline_name}' já existe - substituindo")
        
        pipeline_config = {
            'name': pipeline_name,
            'steps': steps,
            'created_at': datetime.now(),
            'status': 'ready'
        }
        
        self.active_chains[pipeline_name] = pipeline_config
        
        return {
            'pipeline_name': pipeline_name,
            'steps_count': len(steps),
            'status': 'created',
            'created_at': pipeline_config['created_at']
        }
    
    def execute_pipeline(self, pipeline_name: str, input_data: Any = None) -> Dict[str, Any]:
        """Executa um pipeline nomeado"""
        
        if pipeline_name not in self.active_chains:
            raise ValueError(f"Pipeline '{pipeline_name}' não encontrado")
        
        pipeline_config = self.active_chains[pipeline_name]
        steps = pipeline_config['steps']
        
        return self.execute_processor_chain(steps, input_data)
    
    def get_active_chains(self) -> Dict[str, Any]:
        """Retorna informações sobre cadeias ativas"""
        
        return {
            'total_chains': len(self.active_chains),
            'chains': self.active_chains,
            'running_chains': [k for k, v in self.active_chains.items() if v.get('status') == 'running']
        }
    
    def cleanup_completed_chains(self, max_age_hours: int = 24) -> int:
        """Limpa cadeias completadas antigas"""
        
        cutoff_time = datetime.now() - datetime.timedelta(hours=max_age_hours)
        
        chains_to_remove = []
        for chain_id, chain_info in self.active_chains.items():
            if chain_info.get('status') in ['completed', 'failed']:
                completed_at = chain_info.get('completed_at', chain_info.get('started_at'))
                if completed_at and completed_at < cutoff_time:
                    chains_to_remove.append(chain_id)
        
        # Remover cadeias antigas
        for chain_id in chains_to_remove:
            del self.active_chains[chain_id]
        
        self.logger.info(f"Removidas {len(chains_to_remove)} cadeias antigas")
        return len(chains_to_remove)
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do coordenador"""
        
        return {
            'total_active_chains': len(self.active_chains),
            'running_chains': len([c for c in self.active_chains.values() if c.get('status') == 'running']),
            'completed_chains': len([c for c in self.active_chains.values() if c.get('status') == 'completed']),
            'failed_chains': len([c for c in self.active_chains.values() if c.get('status') == 'failed']),
            'registry_stats': self.registry.get_registry_stats()
        }

# Instância global
_processor_coordinator = None

def get_processor_coordinator() -> ProcessorCoordinator:
    """Retorna instância singleton do ProcessorCoordinator"""
    global _processor_coordinator
    if _processor_coordinator is None:
        _processor_coordinator = ProcessorCoordinator()
    return _processor_coordinator 