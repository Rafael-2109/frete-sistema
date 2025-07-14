"""
📁 LOADER MANAGER - Coordenador de Micro-Loaders
==============================================

Manager que coordena todos os micro-loaders especializados.
Responsabilidade: Escolher o loader adequado e coordenar carregamento.
"""

import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime

# TYPE_CHECKING imports para evitar imports circulares
if TYPE_CHECKING:
    from .domain.pedidos_loader import PedidosLoader
    from .domain.entregas_loader import EntregasLoader
    from .domain.fretes_loader import FretesLoader
    from .domain.embarques_loader import EmbarquesLoader
    from .domain.faturamento_loader import FaturamentoLoader
    from .domain.agendamentos_loader import AgendamentosLoader

logger = logging.getLogger(__name__)

# Singleton instance
_loader_manager_instance = None

class LoaderManager:
    """
    Coordenador de micro-loaders especializados.
    
    Responsabilidade: Analisar demanda e escolher o loader
    mais adequado para cada tipo de dados.
    """
    
    _is_initialized = False
    
    def __new__(cls, *args, **kwargs):
        """Implementação do padrão Singleton"""
        global _loader_manager_instance
        if _loader_manager_instance is None:
            _loader_manager_instance = super().__new__(cls)
        return _loader_manager_instance
    
    def __init__(self, scanner=None, mapper=None):
        """Inicializa o manager com lazy loading dos loaders e dependências opcionais"""
        # Evitar reinicialização
        if LoaderManager._is_initialized:
            return
        LoaderManager._is_initialized = True
        
        self.logger = logging.getLogger(f"{__name__}.LoaderManager")
        
        # Dependências injetadas pelo Orchestrator
        self.scanner = scanner
        self.mapper = mapper
        
        # Configuração básica
        self._loaders = {}
        self._loader_mapping = {
            'pedidos': 'pedidos_loader',
            'entregas': 'entregas_loader', 
            'fretes': 'fretes_loader',
            'embarques': 'embarques_loader',
            'faturamento': 'faturamento_loader',
            'agendamentos': 'agendamentos_loader'
        }
        self.initialized = False
        self.db_info = {'tables': {}, 'indexes': {}, 'relationships': {}}
        
        # Se scanner disponível, obter info do banco
        if self.scanner and hasattr(self.scanner, 'get_database_info'):
            try:
                self.db_info = self.scanner.get_database_info()
                logger.info('✅ LoaderManager: Informações do banco obtidas do Scanner')
            except Exception as e:
                logger.warning(f'⚠️ LoaderManager: Erro ao obter info do Scanner: {e}')
        
        self._initialize_loaders()
    
    def _initialize_loaders(self):
        """Inicializa loaders usando lazy loading"""
        try:
            # Importação lazy para evitar dependências circulares
            from .domain.pedidos_loader import get_pedidos_loader
            from .domain.entregas_loader import get_entregas_loader
            from .domain.fretes_loader import get_fretes_loader
            from .domain.embarques_loader import get_embarques_loader
            from .domain.faturamento_loader import get_faturamento_loader
            from .domain.agendamentos_loader import get_agendamentos_loader
            
            # Registrar loaders com lazy loading
            self._loader_factories = {
                'pedidos_loader': get_pedidos_loader,
                'entregas_loader': get_entregas_loader,
                'fretes_loader': get_fretes_loader,
                'embarques_loader': get_embarques_loader,
                'faturamento_loader': get_faturamento_loader,
                'agendamentos_loader': get_agendamentos_loader
            }
            
            self.initialized = True
            self.logger.info("✅ LoaderManager inicializado com 6 micro-loaders")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar LoaderManager: {e}")
            self.initialized = False
    
    def configure_with_scanner(self, scanner):
        """Configura scanner após inicialização"""
        self.scanner = scanner
        if scanner and hasattr(scanner, 'get_database_info'):
            try:
                self.db_info = scanner.get_database_info()
                logger.info('✅ Scanner configurado no LoaderManager')
            except Exception as e:
                logger.warning(f'⚠️ Erro ao configurar Scanner: {e}')
                
    def configure_with_mapper(self, mapper):
        """Configura mapper após inicialização"""
        self.mapper = mapper
        logger.info('✅ Mapper configurado no LoaderManager')
    
    def _get_loader(self, loader_type: str):
        """Obtém loader com lazy loading"""
        if loader_type not in self._loaders:
            if loader_type in self._loader_factories:
                try:
                    self._loaders[loader_type] = self._loader_factories[loader_type]()
                    self.logger.debug(f"📦 Loader {loader_type} carregado com sucesso")
                except Exception as e:
                    self.logger.error(f"❌ Erro ao carregar {loader_type}: {e}")
                    return None
            else:
                self.logger.warning(f"⚠️ Loader type não reconhecido: {loader_type}")
                return None
        
        return self._loaders.get(loader_type)
    
    def load_data_by_domain(self, domain: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados usando o micro-loader específico do domínio.
        
        Args:
            domain: Domínio dos dados (pedidos, entregas, fretes, etc.)
            filters: Filtros específicos para o carregamento
            
        Returns:
            Dict com dados carregados pelo micro-loader especializado
        """
        if not self.initialized:
            return self._error_response("LoaderManager não inicializado", domain)
        
        try:
            # Normalizar domínio
            domain_normalized = domain.lower().strip()
            
            # Mapear para loader específico
            loader_type = self._loader_mapping.get(domain_normalized)
            if not loader_type:
                return self._error_response(f"Domínio não suportado: {domain}", domain)
            
            # Obter loader
            loader = self._get_loader(loader_type)
            if not loader:
                return self._error_response(f"Loader {loader_type} não disponível", domain)
            
            # Executar carregamento específico
            self.logger.debug(f"🎯 Carregando {domain} com {loader_type}")
            
            # Usar método padronizado load_data se disponível
            if hasattr(loader, 'load_data'):
                self.logger.info(f"✅ Usando método padronizado load_data para {domain}")
                data_list = loader.load_data(filters)
                
                # Retornar no formato esperado
                return {
                    'tipo_dados': domain_normalized,
                    'total_registros': len(data_list),
                    'dados_json': data_list,
                    'dados': data_list,  # Compatibilidade
                    'timestamp': datetime.now().isoformat(),
                    'source': 'loader_manager',
                    'optimized': True
                }
            
            # Fallback para métodos específicos (compatibilidade)
            elif domain_normalized == 'pedidos':
                return loader.load_pedidos_data(filters)
            elif domain_normalized == 'entregas':
                return loader.load_entregas_data(filters)
            elif domain_normalized == 'fretes':
                return loader.load_fretes_data(filters)
            elif domain_normalized == 'embarques':
                return loader.load_embarques_data(filters)
            elif domain_normalized == 'faturamento':
                return loader.load_faturamento_data(filters)
            elif domain_normalized == 'agendamentos':
                return loader.load_agendamentos_data(filters)
            else:
                return self._error_response(f"Método de carregamento não implementado para {domain}", domain)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar dados de {domain}: {e}")
            return self._error_response(str(e), domain)
    
    def load_multiple_domains(self, domains: List[str], filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega dados de múltiplos domínios simultaneamente.
        
        Args:
            domains: Lista de domínios a carregar
            filters: Filtros aplicáveis a todos os domínios
            
        Returns:
            Dict com dados de todos os domínios solicitados
        """
        if not self.initialized:
            return self._error_response("LoaderManager não inicializado", "multiple")
        
        try:
            self.logger.info(f"🌐 Carregando múltiplos domínios: {', '.join(domains)}")
            
            results = {
                'tipo_carregamento': 'multiplo',
                'dominios_solicitados': domains,
                'dados': {},
                'estatisticas_gerais': {
                    'total_dominios': len(domains),
                    'dominios_sucesso': 0,
                    'dominios_erro': 0
                },
                'timestamp': datetime.now().isoformat()
            }
            
            for domain in domains:
                try:
                    domain_data = self.load_data_by_domain(domain, filters)
                    
                    if 'erro' not in domain_data:
                        results['dados'][domain] = domain_data
                        results['estatisticas_gerais']['dominios_sucesso'] += 1
                        self.logger.debug(f"✅ {domain} carregado com sucesso")
                    else:
                        results['dados'][domain] = domain_data
                        results['estatisticas_gerais']['dominios_erro'] += 1
                        self.logger.warning(f"⚠️ Erro ao carregar {domain}: {domain_data.get('erro')}")
                        
                except Exception as e:
                    error_data = self._error_response(str(e), domain)
                    results['dados'][domain] = error_data
                    results['estatisticas_gerais']['dominios_erro'] += 1
                    self.logger.error(f"❌ Erro ao carregar {domain}: {e}")
            
            self.logger.info(f"🎯 Carregamento múltiplo concluído: {results['estatisticas_gerais']['dominios_sucesso']}/{len(domains)} sucessos")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erro no carregamento múltiplo: {e}")
            return self._error_response(str(e), "multiple")
    
    def get_best_loader_for_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Analisa consulta e determina o melhor loader.
        
        Args:
            query: Consulta do usuário
            context: Contexto adicional para análise
            
        Returns:
            Nome do domínio/loader mais adequado
        """
        try:
            query_lower = query.lower()
            
            # Palavras-chave por domínio
            domain_keywords = {
                'pedidos': ['pedido', 'cotação', 'cotar', 'pendente', 'falta cotar'],
                'entregas': ['entrega', 'entregar', 'entregue', 'monitoramento', 'atrasada', 'prazo'],
                'fretes': ['frete', 'cte', 'transportadora', 'freight'],
                'embarques': ['embarque', 'embarcar', 'data embarque', 'saída'],
                'faturamento': ['fatura', 'nf', 'nota fiscal', 'valor', 'faturamento'],
                'agendamentos': ['agendamento', 'agendar', 'agendado', 'data prevista']
            }
            
            # Contar matches por domínio
            domain_scores = {}
            for domain, keywords in domain_keywords.items():
                score = sum(1 for keyword in keywords if keyword in query_lower)
                if score > 0:
                    domain_scores[domain] = score
            
            # Aplicar contexto se disponível
            if context:
                if context.get('dominio'):
                    suggested_domain = context['dominio'].lower()
                    if suggested_domain in domain_scores:
                        domain_scores[suggested_domain] += 2  # Boost para sugestão de contexto
                    else:
                        domain_scores[suggested_domain] = 2
            
            # Retornar domínio com maior score
            if domain_scores:
                best_domain = max(domain_scores.keys(), key=lambda x: domain_scores[x])
                self.logger.debug(f"🎯 Melhor loader para '{query[:50]}': {best_domain} (score: {domain_scores[best_domain]})")
                return best_domain
            
            # Fallback: entregas (domínio mais comum)
            self.logger.debug(f"🔄 Usando fallback 'entregas' para: {query[:50]}")
            return 'entregas'
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao determinar melhor loader: {e}")
            return 'entregas'  # Fallback seguro
    
    def get_available_domains(self) -> List[str]:
        """
        Retorna lista de domínios disponíveis.
        
        Returns:
            Lista de domínios suportados
        """
        return list(self._loader_mapping.keys())
    
    def get_loader_status(self) -> Dict[str, Any]:
        """
        Obtém status de todos os loaders.
        
        Returns:
            Dict com status detalhado de cada loader
        """
        status = {
            'manager_initialized': self.initialized,
            'total_loaders': len(self._loader_mapping),
            'loaded_loaders': len(self._loaders),
            'available_domains': self.get_available_domains(),
            'loader_details': {}
        }
        
        for domain, loader_type in self._loader_mapping.items():
            loader = self._loaders.get(loader_type)
            status['loader_details'][domain] = {
                'loader_type': loader_type,
                'loaded': loader is not None,
                'available': loader_type in self._loader_factories
            }
        
        return status
    
    def _error_response(self, error_msg: str, domain: str) -> Dict[str, Any]:
        """Gera resposta de erro padronizada"""
        return {
            'erro': error_msg,
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'total_registros': 0,
            'dados_json': []
        }
    
    def __str__(self) -> str:
        return f"LoaderManager(domains={len(self._loader_mapping)}, loaded={len(self._loaders)})"
    
    def __repr__(self) -> str:
        return f"LoaderManager(initialized={self.initialized})"

def get_loader_manager() -> LoaderManager:
    """
    Retorna instância singleton do LoaderManager.
    
    Returns:
        LoaderManager: Instância do manager
    """
    global _loader_manager_instance
    if _loader_manager_instance is None:
        _loader_manager_instance = LoaderManager()
    return _loader_manager_instance

# Funções de conveniência
def load_domain_data(domain: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Função de conveniência para carregar dados de um domínio"""
    manager = get_loader_manager()
    return manager.load_data_by_domain(domain, filters)

def load_multiple_data(domains: List[str], filters: Dict[str, Any]) -> Dict[str, Any]:
    """Função de conveniência para carregar múltiplos domínios"""
    manager = get_loader_manager()
    return manager.load_multiple_domains(domains, filters)

def get_best_loader(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Função de conveniência para obter melhor loader"""
    manager = get_loader_manager()
    return manager.get_best_loader_for_query(query, context)

# Exports
__all__ = [
    'LoaderManager',
    'get_loader_manager',
    'load_domain_data',
    'load_multiple_data',
    'get_best_loader'
] 