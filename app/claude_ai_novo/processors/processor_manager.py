#!/usr/bin/env python3
"""
ProcessorManager - Gerenciador simplificado de processadores
Reorganizado em módulos menores para melhor manutenibilidade
"""

from .base import ProcessorBase, logging, datetime
from app.claude_ai_novo.utils.flask_context_wrapper import get_flask_context_wrapper
from app.claude_ai_novo.utils.processor_registry import get_processor_registry
from app.claude_ai_novo.coordinators.processor_coordinator import get_processor_coordinator
from typing import Dict, List, Any, Optional

class ProcessorManager(ProcessorBase):
    """
    Gerenciador principal de processadores
    
    Coordena todos os componentes do módulo processors/
    """
    
    def __init__(self):
        super().__init__()
        
        # Componentes principais
        self.flask_wrapper = get_flask_context_wrapper()
        self.registry = get_processor_registry()
        self.coordinator = get_processor_coordinator()
        
        # Status
        self.initialized = True
        self.logger.info("ProcessorManager inicializado com arquitetura modular")
    
    # =====================================
    # MÉTODOS PRINCIPAIS DE PROCESSAMENTO
    # =====================================
    
    def process_context(self, consulta: str, analise: Dict[str, Any]) -> Dict[str, Any]:
        """Processa contexto usando ContextProcessor"""
        
        context_processor = self.registry.get_processor('context')
        if context_processor is None:
            return {'error': 'ContextProcessor não disponível'}
        
        try:
            # Executar carregamento de contexto
            if hasattr(context_processor, 'carregar_contexto_inteligente'):
                return context_processor.carregar_contexto_inteligente(consulta, analise)
            else:
                return {'error': 'Método carregar_contexto_inteligente não disponível'}
                
        except Exception as e:
            error_msg = self._handle_error(e, "process_context")
            return {'error': error_msg}
    
    def process_response(self, consulta: str, analise: Dict[str, Any], 
                        user_context: Optional[Dict] = None) -> str:
        """Processa resposta usando ResponseProcessor"""
        
        response_processor = self.registry.get_processor('response')
        if response_processor is None:
            return "❌ ResponseProcessor não disponível"
        
        try:
            # Executar geração de resposta
            if hasattr(response_processor, 'gerar_resposta_otimizada'):
                return response_processor.gerar_resposta_otimizada(consulta, analise, user_context)
            else:
                return "❌ Método gerar_resposta_otimizada não disponível"
                
        except Exception as e:
            return self._handle_error(e, "process_response")
    
    def process_semantic_loop(self, consulta: str, max_iterations: int = 3) -> Dict[str, Any]:
        """Processa loop semântico usando SemanticLoopProcessor"""
        
        semantic_processor = self.registry.get_processor('semantic_loop')
        if semantic_processor is None:
            return {'error': 'SemanticLoopProcessor não disponível'}
        
        try:
            # Executar loop semântico
            if hasattr(semantic_processor, 'process_semantic_loop'):
                import asyncio
                return asyncio.run(semantic_processor.process_semantic_loop(consulta, max_iterations))
            else:
                return {'error': 'Método process_semantic_loop não disponível'}
                
        except Exception as e:
            error_msg = self._handle_error(e, "process_semantic_loop")
            return {'error': error_msg}
    
    def process_query(self, consulta: str, parametros: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Processa consulta usando QueryProcessor"""
        
        query_processor = self.registry.get_processor('query')
        if query_processor is None:
            return {'error': 'QueryProcessor não disponível'}
        
        try:
            # Executar processamento de query
            if hasattr(query_processor, 'process_query'):
                return query_processor.process_query(consulta, parametros or {})
            else:
                return {'error': 'Método process_query não disponível'}
                
        except Exception as e:
            error_msg = self._handle_error(e, "process_query")
            return {'error': error_msg}
    
    # =====================================
    # MÉTODOS DE COORDENAÇÃO
    # =====================================
    
    def get_processor_chain(self, chain_type: str = "standard") -> List[Dict[str, Any]]:
        """Retorna configuração de cadeia de processadores"""
        
        chains = {
            'standard': [
                {'processor': 'context', 'method': 'carregar_contexto_inteligente'},
                {'processor': 'query', 'method': 'process_query'},
                {'processor': 'response', 'method': 'gerar_resposta_otimizada'}
            ],
            'semantic': [
                {'processor': 'semantic_loop', 'method': 'process_semantic_loop'},
                {'processor': 'context', 'method': 'carregar_contexto_inteligente'},
                {'processor': 'response', 'method': 'gerar_resposta_otimizada'}
            ],
            'advanced': [
                {'processor': 'context', 'method': 'carregar_contexto_inteligente'},
                {'processor': 'semantic_loop', 'method': 'process_semantic_loop'},
                {'processor': 'query', 'method': 'process_query'},
                {'processor': 'response', 'method': 'gerar_resposta_otimizada'}
            ]
        }
        
        return chains.get(chain_type, chains['standard'])
    
    def execute_processing_chain(self, consulta: str, analise: Dict[str, Any], 
                                chain_type: str = "standard") -> Dict[str, Any]:
        """Executa cadeia completa de processamento"""
        
        # Obter configuração da cadeia
        chain_config = self.get_processor_chain(chain_type)
        
        # Preparar dados iniciais
        initial_data = {
            'consulta': consulta,
            'analise': analise,
            'timestamp': datetime.now().isoformat()
        }
        
        # Executar cadeia
        return self.coordinator.execute_processor_chain(chain_config, initial_data)
    
    # =====================================
    # MÉTODOS DE GERENCIAMENTO
    # =====================================
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do manager"""
        
        return {
            'manager': 'ProcessorManager',
            'initialized': self.initialized,
            'architecture': 'modular',
            'components': {
                'flask_wrapper': self.flask_wrapper.get_status(),
                'registry': self.registry.get_registry_stats(),
                'coordinator': self.coordinator.get_coordinator_stats()
            },
            'available_processors': self.registry.list_processors(),
            'health_check': self.health_check()
        }
    
    def health_check(self) -> bool:
        """Verifica saúde geral do sistema"""
        
        if not self.initialized:
            return False
        
        # Verificar componentes principais
        components_ok = all([
            self.flask_wrapper.health_check(),
            self.registry.health_check(),
            self.coordinator.health_check()
        ])
        
        return components_ok
    
    def get_detailed_health_report(self) -> Dict[str, Any]:
        """Retorna relatório detalhado de saúde"""
        
        return {
            'overall_health': self.health_check(),
            'component_health': {
                'flask_wrapper': self.flask_wrapper.health_check(),
                'registry': self.registry.health_check(),
                'coordinator': self.coordinator.health_check()
            },
            'processor_validation': self.registry.validate_all_processors(),
            'flask_context_info': self.flask_wrapper.get_flask_context_info(),
            'active_chains': self.coordinator.get_active_chains(),
            'timestamp': datetime.now().isoformat()
        }
    
    def reload_processors(self) -> Dict[str, Any]:
        """Recarrega todos os processadores"""
        
        results = {}
        
        for processor_name in self.registry.list_processors():
            try:
                success = self.registry.reload_processor(processor_name)
                results[processor_name] = {'reloaded': success}
                
            except Exception as e:
                results[processor_name] = {'error': str(e)}
        
        return {
            'total_processors': len(results),
            'successful_reloads': sum(1 for r in results.values() if r.get('reloaded')),
            'results': results
        }
    
    def cleanup_resources(self) -> Dict[str, Any]:
        """Limpa recursos não utilizados"""
        
        cleanup_results = {}
        
        # Limpar cadeias antigas
        try:
            cleaned_chains = self.coordinator.cleanup_completed_chains()
            cleanup_results['cleaned_chains'] = cleaned_chains
        except Exception as e:
            cleanup_results['cleanup_error'] = str(e)
        
        cleanup_results['cleanup_timestamp'] = datetime.now().isoformat()
        
        return cleanup_results
    
    def __str__(self) -> str:
        return f"ProcessorManager(modular, {len(self.registry.list_processors())} processors)"
    
    def __repr__(self) -> str:
        return f"ProcessorManager(initialized={self.initialized}, architecture=modular)"
    
    def set_memory_manager(self, memory_manager):
        """
        Configura memory manager para enriquecer respostas.
        
        Args:
            memory_manager: Instância do MemoryManager
        """
        try:
            self.memory_manager = memory_manager
            self.logger.info("✅ Memory Manager configurado no ProcessorManager")
            
            # Propagar para ResponseProcessor se disponível
            response_processor = self.registry.get_processor('response')
            if response_processor and hasattr(response_processor, 'set_memory_manager'):
                response_processor.set_memory_manager(memory_manager)
                self.logger.info("✅ Memory Manager propagado para ResponseProcessor")
                
            # Propagar para ContextProcessor se disponível
            context_processor = self.registry.get_processor('context')
            if context_processor and hasattr(context_processor, 'set_memory_manager'):
                context_processor.set_memory_manager(memory_manager)
                self.logger.info("✅ Memory Manager propagado para ContextProcessor")
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao configurar Memory Manager: {e}")
            return False

# =====================================
# INSTÂNCIAS GLOBAIS E CONVENIÊNCIA
# ====================================

# Instância global do manager
_processor_manager = None

def get_processor_manager() -> ProcessorManager:
    """Retorna instância singleton do ProcessorManager"""
    global _processor_manager
    if _processor_manager is None:
        _processor_manager = ProcessorManager()
    return _processor_manager

# Aliases para compatibilidade
def get_processormanager() -> ProcessorManager:
    """Alias para get_processor_manager()"""
    return get_processor_manager()

def get_manager() -> ProcessorManager:
    """Alias para get_processor_manager()"""
    return get_processor_manager()

# =====================================
# TESTE E VALIDAÇÃO
# =====================================
    
    def set_memory(self, memory_manager):
        """Configura o MemoryManager para processamento integrado"""
        try:
            self.memory_manager = memory_manager
            
            # Propagar para processadores que precisam
            for name, processor in self.processors.items():
                if hasattr(processor, 'set_memory'):
                    processor.set_memory(memory_manager)
                    
            logger.info("✅ MemoryManager configurado no ProcessorManager")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar memory: {e}")

if __name__ == "__main__":
    # Teste básico da arquitetura modular
    manager = get_processor_manager()
    
    print("=== TESTE DA ARQUITETURA MODULAR ===")
    print(f"Manager: {manager}")
    print(f"Status: {manager.get_status()}")
    print(f"Health: {manager.health_check()}")
    
    # Teste de cadeia de processamento
    print("\n=== TESTE DE CADEIA PADRÃO ===")
    chain = manager.get_processor_chain("standard")
    print(f"Cadeia padrão: {chain}")
    
    print("\n=== RELATÓRIO DE SAÚDE DETALHADO ===")
    health_report = manager.get_detailed_health_report()
    print(f"Relatório: {health_report}")
    
    print("\n=== ARQUITETURA MODULAR TESTADA COM SUCESSO ===")