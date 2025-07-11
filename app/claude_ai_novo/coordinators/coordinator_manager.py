"""
🎯 COORDINATOR MANAGER - Gerenciador Central de Coordenadores
=============================================================

Responsabilidade: COORDENAR todos os coordenadores e agentes do sistema.
Especializações: Orquestração, Distribuição de Tarefas, Seleção Inteligente, Monitoramento.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class MockSpecialistAgent:
    """Mock para SpecialistAgent quando não consegue carregar corretamente"""
    
    def __init__(self):
        self.agent_type = "mock"
        logger.info("🔧 MockSpecialistAgent inicializado como fallback")
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None):
        return {
            'status': 'mock_response',
            'message': 'SpecialistAgent em modo mock',
            'query': query,
            'agent_type': self.agent_type
        }
    
    def coordinate_specialists(self, query: str, context: Optional[Dict[str, Any]] = None):
        return self.process_query(query, context)

class CoordinatorType(Enum):
    """Tipos de coordenadores disponíveis."""
    INTELLIGENCE = "intelligence"
    PROCESSOR = "processor"
    SPECIALIST = "specialist"
    DOMAIN_AGENT = "domain_agent"

class CoordinatorManager:
    """
    Gerenciador central que coordena todos os coordenadores do sistema.
    
    Responsabilidades:
    - Coordenar IntelligenceCoordinator, ProcessorCoordinator e SpecialistAgent
    - Gerenciar Domain Agents especializados
    - Distribuir tarefas inteligentemente
    - Monitorar performance dos coordenadores
    """
    
    def __init__(self):
        """Inicializa o gerenciador de coordenadores."""
        self.coordinators: Dict[str, Any] = {}
        self.domain_agents: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        self.initialized = False
        
        self._initialize_coordinators()
        logger.info("🎯 CoordinatorManager inicializado")
    
    def _initialize_coordinators(self):
        """Inicializa todos os coordenadores disponíveis."""
        try:
            # Intelligence Coordinator
            self._load_intelligence_coordinator()
            
            # Processor Coordinator
            self._load_processor_coordinator()
            
            # Specialist Coordinator
            self._load_specialist_coordinator()
            
            # Domain Agents
            self._load_domain_agents()
            
            self.initialized = True
            logger.info("✅ Todos os coordenadores inicializados com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar coordenadores: {e}")
            self.initialized = False
    
    def _load_intelligence_coordinator(self):
        """Carrega o Intelligence Coordinator."""
        try:
            from .intelligence_coordinator import get_intelligence_coordinator
            coordinator = get_intelligence_coordinator()
            if coordinator:
                self.coordinators['intelligence'] = coordinator
                self.performance_metrics['intelligence'] = {
                    'loaded_at': datetime.now().isoformat(),
                    'queries_processed': 0,
                    'status': 'active'
                }
                logger.info("✅ IntelligenceCoordinator carregado")
            else:
                logger.warning("⚠️ IntelligenceCoordinator não disponível")
        except ImportError as e:
            logger.warning(f"⚠️ Não foi possível carregar IntelligenceCoordinator: {e}")
    
    def _load_processor_coordinator(self):
        """Carrega o Processor Coordinator."""
        try:
            from .processor_coordinator import ProcessorCoordinator
            coordinator = ProcessorCoordinator()
            self.coordinators['processor'] = coordinator
            self.performance_metrics['processor'] = {
                'loaded_at': datetime.now().isoformat(),
                'processes_handled': 0,
                'status': 'active'
            }
            logger.info("✅ ProcessorCoordinator carregado")
        except ImportError as e:
            logger.warning(f"⚠️ Não foi possível carregar ProcessorCoordinator: {e}")
    
    def _load_specialist_coordinator(self):
        """Carrega o Specialist Coordinator."""
        try:
            # Nota: specialist_agents.py deveria ser specialist_coordinator.py
            from .specialist_agents import SpecialistAgent
            from app.claude_ai_novo.utils.agent_types import AgentType
            
            # SpecialistAgent precisa de agent_type obrigatório
            coordinator = SpecialistAgent(AgentType.FRETES)  # Usando FRETES como default
            self.coordinators['specialist'] = coordinator
            self.performance_metrics['specialist'] = {
                'loaded_at': datetime.now().isoformat(),
                'specializations_handled': 0,
                'status': 'active'
            }
            logger.info("✅ SpecialistAgent carregado")
        except ImportError as e:
            logger.warning(f"⚠️ Não foi possível carregar SpecialistAgent: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao instanciar SpecialistAgent: {e}")
            # Criar fallback mock
            self.coordinators['specialist'] = MockSpecialistAgent()
            logger.info("✅ SpecialistAgent mock carregado como fallback")
    
    def _load_domain_agents(self):
        """Carrega todos os Domain Agents especializados."""
        domain_types = ['embarques', 'entregas', 'financeiro', 'fretes', 'pedidos']
        
        for domain in domain_types:
            try:
                # Importação dinâmica dos agentes
                module_name = f".domain_agents.{domain}_agent"
                class_name = f"{domain.title()}Agent"
                
                module = __import__(f"app.claude_ai_novo.coordinators{module_name}", 
                                  fromlist=[class_name])
                agent_class = getattr(module, class_name)
                
                # Criar instância do agente
                agent = agent_class()
                self.domain_agents[domain] = agent
                
                self.performance_metrics[f'agent_{domain}'] = {
                    'loaded_at': datetime.now().isoformat(),
                    'domain_queries': 0,
                    'status': 'active'
                }
                
                logger.info(f"✅ {class_name} carregado para domínio '{domain}'")
                
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível carregar agente para '{domain}': {e}")
    
    def coordinate_query(self, query: str, context: Optional[Dict[str, Any]] = None, 
                        preferred_coordinator: Optional[str] = None) -> Dict[str, Any]:
        """
        Coordena uma consulta distribuindo para o coordenador mais adequado.
        
        Args:
            query: Consulta a ser processada
            context: Contexto da consulta
            preferred_coordinator: Coordenador preferencial (opcional)
            
        Returns:
            Resultado da coordenação
        """
        try:
            if not self.initialized:
                return {
                    'status': 'error',
                    'message': 'Coordenadores não inicializados',
                    'coordinator_used': None
                }
            
            # Determinar melhor coordenador
            coordinator_name = preferred_coordinator or self._select_best_coordinator(query, context)
            
            # Processar com coordenador selecionado
            result = self._process_with_coordinator(coordinator_name, query, context)
            
            # Atualizar métricas
            self._update_metrics(coordinator_name)
            
            return {
                'status': 'success',
                'result': result,
                'coordinator_used': coordinator_name,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na coordenação da consulta: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'coordinator_used': None
            }
    
    def _select_best_coordinator(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Seleciona o melhor coordenador baseado na consulta e contexto."""
        query_lower = query.lower()
        
        # Detecção de domínio específico
        domain_keywords = {
            'embarques': ['embarque', 'embarques', 'expedicao', 'expedição'],
            'entregas': ['entrega', 'entregas', 'entregar', 'entregue'],
            'financeiro': ['financeiro', 'faturamento', 'pagamento', 'valor'],
            'fretes': ['frete', 'fretes', 'transportadora', 'transporte'],
            'pedidos': ['pedido', 'pedidos', 'cotacao', 'cotação']
        }
        
        # Verificar se é consulta de domínio específico
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                if domain in self.domain_agents:
                    return f'agent_{domain}'
        
        # Verificar complexidade para Intelligence Coordinator
        if any(word in query_lower for word in ['analisar', 'insights', 'padrões', 'tendências']):
            if 'intelligence' in self.coordinators:
                return 'intelligence'
        
        # Verificar processamento para Processor Coordinator
        if any(word in query_lower for word in ['processar', 'executar', 'workflow']):
            if 'processor' in self.coordinators:
                return 'processor'
        
        # Fallback para Intelligence se disponível
        if 'intelligence' in self.coordinators:
            return 'intelligence'
        elif 'processor' in self.coordinators:
            return 'processor'
        else:
            return 'specialist'
    
    def _process_with_coordinator(self, coordinator_name: str, query: str, 
                                 context: Optional[Dict[str, Any]]) -> Any:
        """Processa consulta com o coordenador especificado."""
        
        # Domain Agents
        if coordinator_name.startswith('agent_'):
            domain = coordinator_name[6:]  # Remove 'agent_'
            if domain in self.domain_agents:
                agent = self.domain_agents[domain]
                return agent.process_query(query, context or {})
            else:
                raise ValueError(f"Domain agent '{domain}' não encontrado")
        
        # Coordinators principais
        elif coordinator_name in self.coordinators:
            coordinator = self.coordinators[coordinator_name]
            
            if coordinator_name == 'intelligence':
                # IntelligenceCoordinator tem método específico
                return coordinator.coordinate_intelligent_response(query, context or {})
            elif coordinator_name == 'processor':
                # ProcessorCoordinator tem método específico
                return coordinator.process_query(query, context or {})
            elif coordinator_name == 'specialist':
                # SpecialistCoordinator tem método específico
                return coordinator.coordinate_specialists(query, context or {})
            else:
                # Método genérico
                return coordinator.process(query, context or {})
        else:
            raise ValueError(f"Coordenador '{coordinator_name}' não encontrado")
    
    def _update_metrics(self, coordinator_name: str):
        """Atualiza métricas de performance do coordenador."""
        if coordinator_name in self.performance_metrics:
            metrics = self.performance_metrics[coordinator_name]
            
            if coordinator_name == 'intelligence':
                metrics['queries_processed'] += 1
            elif coordinator_name == 'processor':
                metrics['processes_handled'] += 1
            elif coordinator_name == 'specialist':
                metrics['specializations_handled'] += 1
            elif coordinator_name.startswith('agent_'):
                metrics['domain_queries'] += 1
            
            metrics['last_used'] = datetime.now().isoformat()
    
    def get_coordinator_status(self) -> Dict[str, Any]:
        """Retorna status detalhado de todos os coordenadores."""
        return {
            'initialized': self.initialized,
            'coordinators_available': list(self.coordinators.keys()),
            'domain_agents_available': list(self.domain_agents.keys()),
            'total_coordinators': len(self.coordinators) + len(self.domain_agents),
            'performance_metrics': self.performance_metrics,
            'status_checked_at': datetime.now().isoformat()
        }
    
    def get_best_coordinator_for_domain(self, domain: str) -> Optional[str]:
        """Retorna o melhor coordenador para um domínio específico."""
        if domain in self.domain_agents:
            return f'agent_{domain}'
        elif 'intelligence' in self.coordinators:
            return 'intelligence'
        else:
            return None
    
    def reload_coordinator(self, coordinator_name: str) -> bool:
        """Recarrega um coordenador específico."""
        try:
            if coordinator_name == 'intelligence':
                self._load_intelligence_coordinator()
            elif coordinator_name == 'processor':
                self._load_processor_coordinator()
            elif coordinator_name == 'specialist':
                self._load_specialist_coordinator()
            elif coordinator_name.startswith('agent_'):
                domain = coordinator_name[6:]
                # Reload específico do domain agent
                self._load_domain_agents()
            else:
                return False
            
            logger.info(f"🔄 Coordenador '{coordinator_name}' recarregado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao recarregar coordenador '{coordinator_name}': {e}")
            return False


# Instância global para conveniência
_coordinator_manager = None

def get_coordinator_manager() -> CoordinatorManager:
    """
    Retorna instância global do CoordinatorManager.
    
    Returns:
        Instância do CoordinatorManager
    """
    global _coordinator_manager
    if _coordinator_manager is None:
        _coordinator_manager = CoordinatorManager()
    return _coordinator_manager

def coordinate_intelligent_query(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Função de conveniência para coordenar consultas inteligentemente.
    
    Args:
        query: Consulta a ser processada
        context: Contexto da consulta
        
    Returns:
        Resultado da coordenação
    """
    manager = get_coordinator_manager()
    return manager.coordinate_query(query, context)

def get_domain_agent(domain: str) -> Optional[Any]:
    """
    Função de conveniência para obter agente de domínio específico.
    
    Args:
        domain: Nome do domínio (embarques, entregas, etc.)
        
    Returns:
        Instância do agente ou None se não encontrado
    """
    manager = get_coordinator_manager()
    return manager.domain_agents.get(domain)

def get_coordination_status() -> Dict[str, Any]:
    """
    Função de conveniência para obter status da coordenação.
    
    Returns:
        Status completo do sistema de coordenação
    """
    manager = get_coordinator_manager()
    return manager.get_coordinator_status() 