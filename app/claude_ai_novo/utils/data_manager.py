#!/usr/bin/env python3
"""
DataManager - Centralizar acesso a dados e providers
Baseado no padrão do AnalyzerManager
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncio
from datetime import datetime

# Imports dos componentes reais com fallbacks
# DataExecutor removido - funcionalidade redundante

try:
    from app.claude_ai_novo.providers.data_provider import SistemaRealData as RealSistemaRealData
    SistemaRealData = RealSistemaRealData
except ImportError:
    class FallbackSistemaRealData:
        """Fallback para SistemaRealData"""
        def __init__(self):
            pass
    SistemaRealData = FallbackSistemaRealData

# DatabaseLoader removido - funcionalidade consolidada no data_provider

try:
    from app.claude_ai_novo.loaders.context_loader import ContextLoader as RealContextLoader
    ContextLoader = RealContextLoader
except ImportError:
    class FallbackContextLoader:
        """Fallback para ContextLoader"""
        def __init__(self):
            pass
    ContextLoader = FallbackContextLoader

# Import da classe base centralizada
from app.claude_ai_novo.utils.base_context_manager import BaseContextManager

logger = logging.getLogger(__name__)

class DataManager(BaseContextManager):
    """
    Centralizar acesso a dados e providers
    
    Gerencia e coordena todos os componentes da pasta data
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.DataManager")
        self.components = {}
        self.initialized = False
        self._initialized = True  # Marcar como inicializado no contexto base
        
        # Inicializar componentes
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa todos os componentes gerenciados"""
        
        try:
            # DataExecutor removido - funcionalidade redundante

            # Inicializar SistemaRealData
            try:
                self.components['provider'] = SistemaRealData()
                self.logger.debug(f"SistemaRealData inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar SistemaRealData: {e}")
                self.components['provider'] = None

            # DatabaseLoader removido - funcionalidade consolidada no data_provider

            # Inicializar ContextLoader
            try:
                self.components['context'] = ContextLoader()
                self.logger.debug(f"ContextLoader inicializado")
            except Exception as e:
                self.logger.warning(f"Erro ao inicializar ContextLoader: {e}")
                self.components['context'] = None
            
            self.initialized = True
            self.logger.info(f"DataManager inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar DataManager: {e}")
            raise
    
    def load_data(self, consulta: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Carrega dados usando providers disponíveis
        
        Args:
            consulta: Consulta do usuário
            user_context: Contexto do usuário
            
        Returns:
            Dict com dados carregados
        """
        
        if not self.initialized:
            raise RuntimeError(f"DataManager não foi inicializado")
        
        try:
            self.logger.debug(f"🔍 Carregando dados para: {consulta[:50]}...")
            
            # Usar provider como fonte principal de dados
            if self.components.get('provider'):
                provider = self.components['provider']
                return {
                    'success': True,
                    'consulta': consulta,
                    'data_source': 'SistemaRealData',
                    'timestamp': datetime.now().isoformat(),
                    'provider_available': True
                }
            else:
                return {
                    'error': 'Nenhum provider de dados disponível',
                    'fallback': True,
                    'consulta': consulta,
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar dados: {e}")
            return {
                'error': str(e),
                'consulta': consulta,
                'timestamp': datetime.now().isoformat()
            }

    def load_context(self, analise: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega contexto inteligente
        
        Args:
            analise: Análise da consulta
            
        Returns:
            Dict com contexto carregado
        """
        
        if not self.initialized:
            raise RuntimeError(f"DataManager não foi inicializado")
        
        try:
            self.logger.debug(f"🧠 Carregando contexto inteligente...")
            
            if self.components.get('context'):
                return self.components['context']._carregar_contexto_inteligente(analise)
            else:
                return {
                    'error': 'ContextLoader não disponível',
                    'fallback': True,
                    'analise': analise,
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar contexto: {e}")
            return {
                'error': str(e),
                'analise': analise,
                'timestamp': datetime.now().isoformat()
            }

    def provide_data(self, tipo_dados: str = 'system_prompt') -> Dict[str, Any]:
        """
        Fornece dados do sistema real
        
        Args:
            tipo_dados: Tipo de dados ('system_prompt', 'relatorio', 'clientes', etc.)
            
        Returns:
            Dict com dados do sistema
        """
        
        if not self.initialized:
            raise RuntimeError(f"DataManager não foi inicializado")
        
        try:
            self.logger.debug(f"📊 Fornecendo dados do tipo: {tipo_dados}")
            
            if not self.components.get('provider'):
                return {
                    'error': 'SistemaRealData não disponível',
                    'fallback': True,
                    'tipo_dados': tipo_dados
                }
            
            provider = self.components['provider']
            
            if tipo_dados == 'system_prompt':
                return {'system_prompt': provider.gerar_system_prompt_real()}
            elif tipo_dados == 'relatorio':
                return {'relatorio': provider.gerar_relatorio_dados_sistema()}
            elif tipo_dados == 'clientes':
                return {'clientes': provider.buscar_clientes_reais()}
            elif tipo_dados == 'transportadoras':
                return {'transportadoras': provider.buscar_transportadoras_reais()}
            elif tipo_dados == 'modelos':
                return {'modelos': provider.buscar_todos_modelos_reais()}
            else:
                return {'error': f'Tipo de dados não suportado: {tipo_dados}'}
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao fornecer dados: {e}")
            return {
                'error': str(e),
                'tipo_dados': tipo_dados
            }

    def get_loader(self, tipo_loader: str = 'context') -> Any:
        """
        Retorna loader específico
        
        Args:
            tipo_loader: Tipo do loader ('context', 'provider')
            
        Returns:
            Instância do loader ou None
        """
        
        if not self.initialized:
            raise RuntimeError(f"DataManager não foi inicializado")
        
        try:
            if tipo_loader == 'context':
                return self.components.get('context')
            elif tipo_loader == 'provider':
                return self.components.get('provider')
            else:
                self.logger.warning(f"Tipo de loader não reconhecido: {tipo_loader}")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter loader: {e}")
            return None

    def get_provider(self) -> Any:
        """
        Retorna provider de dados reais
        
        Returns:
            Instância do SistemaRealData ou None
        """
        
        if not self.initialized:
            raise RuntimeError(f"DataManager não foi inicializado")
        
        try:
            return self.components.get('provider')
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter provider: {e}")
            return None

    def validate_client(self, nome_cliente: str) -> Dict[str, Any]:
        """
        Valida se cliente existe no sistema
        
        Args:
            nome_cliente: Nome do cliente para validar
            
        Returns:
            Dict com resultado da validação
        """
        
        if not self.initialized:
            raise RuntimeError(f"DataManager não foi inicializado")
        
        try:
            if not self.components.get('provider'):
                return {
                    'exists': False,
                    'error': 'SistemaRealData não disponível'
                }
            
            provider = self.components['provider']
            exists = provider.validar_cliente_existe(nome_cliente)
            
            result = {
                'cliente': nome_cliente,
                'exists': exists,
                'timestamp': datetime.now().isoformat()
            }
            
            if not exists:
                # Sugerir clientes similares
                sugestoes = provider.sugerir_cliente_similar(nome_cliente)
                result['suggestions'] = sugestoes
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao validar cliente: {e}")
            return {
                'cliente': nome_cliente,
                'exists': False,
                'error': str(e)
            }

    def get_best_loader(self, consulta: str, data_type: str = 'general') -> str:
        """
        Determina o melhor loader para uma consulta específica
        
        Args:
            consulta: Consulta do usuário
            data_type: Tipo de dados ('general', 'context', 'provider', 'real_time')
            
        Returns:
            Nome do melhor loader
        """
        
        if not self.initialized:
            raise RuntimeError(f"DataManager não foi inicializado")
        
        try:
            consulta_lower = consulta.lower()
            
            # Casos específicos primeiro
            if data_type == 'context' or any(word in consulta_lower for word in ['contexto', 'inteligente', 'específico']):
                if self.components.get('context'):
                    return 'context'
            
            elif data_type == 'provider' or any(word in consulta_lower for word in ['banco', 'dados', 'tabela']):
                # database loader removido - usar provider
                if self.components.get('provider'):
                    return 'provider'
            
            elif data_type == 'real_time' or any(word in consulta_lower for word in ['agora', 'atual', 'hoje']):
                if self.components.get('provider'):
                    return 'provider'
            
            # Análise automática baseada na complexidade
            word_count = len(consulta.split())
            
            if word_count > 15:  # Consulta complexa
                if self.components.get('context'):
                    return 'context'
                elif self.components.get('provider'):
                    return 'provider'
            
            else:  # Consulta simples
                if self.components.get('provider'):
                    return 'provider'
                elif self.components.get('context'):
                    return 'context'
            
            # Fallback: primeiro loader disponível
            for name, component in self.components.items():
                if component is not None:
                    return name
            
            return 'none'
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao escolher melhor loader: {e}")
            return 'error'
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do manager"""
        
        return {
            'manager': 'DataManager',
            'initialized': self.initialized,
            'components': list(self.components.keys()),
            'total_components': len(self.components),
            'function': 'Centralizar acesso a dados e providers'
        }
    
    def health_check(self) -> bool:
        """Verifica se o manager está funcionando"""
        
        if not self.initialized:
            return False
        
        # Verificar se pelo menos um componente está funcionando
        componentes_funcionais = 0
        for name, component in self.components.items():
            if component is not None:
                componentes_funcionais += 1
            else:
                self.logger.warning(f"Componente {name} não está disponível")
        
        # Manager está saudável se pelo menos 2 componentes estão funcionando
        return componentes_funcionais >= 2
    
    def __str__(self) -> str:
        return f"DataManager(components={len(self.components)})"
    
    def __repr__(self) -> str:
        return f"DataManager(initialized={self.initialized})"

# Instância global do manager
datamanager_instance = None

def get_datamanager() -> DataManager:
    """Retorna instância singleton do DataManager"""
    
    global datamanager_instance
    
    if datamanager_instance is None:
        datamanager_instance = DataManager()
    
    return datamanager_instance

# Função de conveniência para compatibilidade
def get_manager() -> DataManager:
    """Alias para get_datamanager()"""
    return get_datamanager()

if __name__ == "__main__":
    # Teste básico
    manager = get_datamanager()
    print(f"Manager: {manager}")
    print(f"Status: {manager.get_status()}")
    print(f"Health: {manager.health_check()}")