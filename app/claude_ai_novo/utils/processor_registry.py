#!/usr/bin/env python3
"""
ProcessorRegistry - Registro e gerenciamento de processadores
Extraído do processor_manager.py para melhor organização
"""

from app.claude_ai_novo.processors.base import BaseProcessor, logging
from typing import Dict, Any, Optional, Type, List
from app.claude_ai_novo.utils.flask_context_wrapper import get_flask_context_wrapper

class ProcessorRegistry(BaseProcessor):
    """Registro centralizado de processadores"""
    
    def __init__(self):
        super().__init__()
        self.processors = {}
        self.processor_types = {}
        self.flask_wrapper = get_flask_context_wrapper()
        self._initialize_processors()
    
    def _initialize_processors(self):
        """Inicializa todos os processadores disponíveis"""
        
        # Definir processadores disponíveis - TODOS os processadores existentes
        processor_configs = [
            {
                'name': 'context',
                'class_name': 'ContextProcessor',
                'module': 'context_processor',
                'description': 'Processamento de contexto inteligente'
            },
            {
                'name': 'response',
                'class_name': 'ResponseProcessor', 
                'module': 'response_processor',
                'description': 'Processamento de respostas otimizadas'
            },
            {
                'name': 'semantic_loop',
                'class_name': 'SemanticLoopProcessor',
                'module': 'semantic_loop_processor',
                'description': 'Loop semântico-lógico'
            },
            {
                'name': 'query',
                'class_name': 'QueryProcessor',
                'module': 'query_processor',
                'description': 'Processamento de consultas'
            },
            {
                'name': 'intelligence',
                'class_name': 'IntelligenceProcessor',
                'module': 'intelligence_processor',
                'description': 'Processamento de inteligência artificial'
            },
            {
                'name': 'data',
                'class_name': 'DataProcessor',
                'module': 'data_processor',
                'description': 'Processamento de dados'
            }
        ]
        
        # Registrar cada processador
        for config in processor_configs:
            self._register_processor(config)
        
        self.logger.info(f"Registry inicializado com {len(self.processors)} processadores")
    
    def _register_processor(self, config: Dict[str, str]):
        """Registra um processador específico"""
        
        name = config['name']
        
        try:
            class_name = config['class_name']
            module_name = config['module']
            
            # Tentar múltiplas formas de importar para evitar erro de globals
            processor_instance = None
            
            try:
                # Método 1: Import absoluto
                full_module_name = f"app.claude_ai_novo.processors.{module_name}"
                module = __import__(full_module_name, fromlist=[class_name])
                processor_class = getattr(module, class_name)
                processor_instance = processor_class()
                
                self.logger.debug(f"✅ Processador '{name}' registrado (método absoluto)")
                
            except (ImportError, AttributeError) as e1:
                try:
                    # Método 2: Import relativo seguro
                    if __name__ and '.' in __name__:
                        module_name_rel = f"..processors.{module_name}"
                        module = __import__(module_name_rel, fromlist=[class_name], level=1)
                        processor_class = getattr(module, class_name)
                        processor_instance = processor_class()
                        
                        self.logger.debug(f"✅ Processador '{name}' registrado (método relativo)")
                    else:
                        raise ImportError("Contexto de módulo inadequado para import relativo")
                        
                except (ImportError, AttributeError) as e2:
                    self.logger.warning(f"⚠️ Não foi possível importar {class_name}: {e1}, {e2}")
                    processor_instance = None
            
            if processor_instance:
                # Registrar com sucesso
                self.processors[name] = processor_instance
                self.processor_types[name] = type(processor_instance)
            else:
                # Criar fallback
                self.logger.warning(f"Usando fallback para {name}")
                self.processors[name] = self._create_fallback_processor(name, config)
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar processador '{name}': {e}")
            # Criar fallback
            self.processors[name] = self._create_fallback_processor(name, config)
    
    def _create_fallback_processor(self, name: str, config: Dict[str, str]) -> Any:
        """Cria processador de fallback"""
        
        class FallbackProcessor(BaseProcessor):
            def __init__(self, processor_name: str, processor_config: Dict[str, str]):
                super().__init__()
                self.name = processor_name
                self.config = processor_config
                self.logger.warning(f"Usando fallback para {processor_name}")
            
            def process(self, *args, **kwargs):
                return {
                    'processor': self.name,
                    'status': 'fallback',
                    'message': f"Processador {self.name} não disponível",
                    'config': self.config
                }
        
        return FallbackProcessor(name, config)
    
    def get_processor(self, name: str) -> Optional[Any]:
        """Retorna processador pelo nome"""
        
        processor = self.processors.get(name)
        
        if processor is None:
            self.logger.warning(f"Processador '{name}' não encontrado")
            return None
        
        return processor
    
    def get_processor_type(self, name: str) -> Optional[Type]:
        """Retorna tipo do processador pelo nome"""
        return self.processor_types.get(name)
    
    def list_processors(self) -> List[str]:
        """Lista todos os processadores registrados"""
        return list(self.processors.keys())
    
    def get_processor_info(self, name: str) -> Dict[str, Any]:
        """Retorna informações detalhadas do processador"""
        
        processor = self.processors.get(name)
        
        if processor is None:
            return {'error': f"Processador '{name}' não encontrado"}
        
        info = {
            'name': name,
            'type': type(processor).__name__,
            'available': processor is not None,
            'initialized': getattr(processor, 'initialized', True),
            'health': self._check_processor_health(processor)
        }
        
        # Adicionar informações específicas se disponível
        if hasattr(processor, 'get_status'):
            try:
                info['status'] = processor.get_status()
            except Exception as e:
                info['status_error'] = str(e)
        
        return info
    
    def _check_processor_health(self, processor: Any) -> bool:
        """Verifica saúde do processador"""
        
        try:
            # Verificar se tem método health_check
            if hasattr(processor, 'health_check'):
                return processor.health_check()
            
            # Verificar se tem método initialized
            if hasattr(processor, 'initialized'):
                return processor.initialized
            
            # Se chegou aqui, considera saudável
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar saúde do processador: {e}")
            return False
    
    def reload_processor(self, name: str) -> bool:
        """Recarrega um processador específico"""
        
        if name not in self.processors:
            self.logger.error(f"Processador '{name}' não existe")
            return False
        
        try:
            # Encontrar configuração original
            processor_configs = [
                {'name': 'context', 'class_name': 'ContextProcessor', 'module': 'context_processor'},
                {'name': 'response', 'class_name': 'ResponseProcessor', 'module': 'response_processor'},
                {'name': 'semantic_loop', 'class_name': 'SemanticLoopProcessor', 'module': 'semantic_loop_processor'},
                {'name': 'query', 'class_name': 'QueryProcessor', 'module': 'query_processor'}
            ]
            
            config = next((c for c in processor_configs if c['name'] == name), None)
            
            if config is None:
                self.logger.error(f"Configuração para '{name}' não encontrada")
                return False
            
            # Registrar novamente
            self._register_processor(config)
            
            self.logger.info(f"Processador '{name}' recarregado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao recarregar processador '{name}': {e}")
            return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do registry"""
        
        stats = {
            'total_processors': len(self.processors),
            'available_processors': sum(1 for p in self.processors.values() if p is not None),
            'healthy_processors': sum(1 for p in self.processors.values() if self._check_processor_health(p)),
            'processor_names': list(self.processors.keys()),
            'flask_context_available': self.flask_wrapper.is_flask_available()
        }
        
        return stats
    
    def validate_all_processors(self) -> Dict[str, Any]:
        """Valida todos os processadores registrados"""
        
        validation_results = {}
        
        for name, processor in self.processors.items():
            try:
                validation_results[name] = {
                    'available': processor is not None,
                    'health': self._check_processor_health(processor),
                    'type': type(processor).__name__,
                    'methods': [method for method in dir(processor) if not method.startswith('_')]
                }
            except Exception as e:
                validation_results[name] = {
                    'error': str(e),
                    'available': False,
                    'health': False
                }
        
        return validation_results

# Instância global
_processor_registry = None

def get_processor_registry() -> ProcessorRegistry:
    """Retorna instância singleton do ProcessorRegistry"""
    global _processor_registry
    if _processor_registry is None:
        _processor_registry = ProcessorRegistry()
    return _processor_registry 