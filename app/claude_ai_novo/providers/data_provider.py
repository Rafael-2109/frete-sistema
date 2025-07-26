#!/usr/bin/env python3
"""
📊 DATA PROVIDER - Provedor de Dados
===================================

Módulo responsável por fornecer dados para o sistema Claude AI Novo.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta, date

# Flask fallback para execução standalone
try:
    from app.claude_ai_novo.utils.flask_fallback import get_model, get_db, get_current_user
    FLASK_FALLBACK_AVAILABLE = True
except ImportError:
    # Fallback quando não há Flask
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
            def __call__(self, *args, **kwargs):
                return self
            def __getattr__(self, name):
                return self
    get_model = get_db = get_current_user = Mock
    FLASK_FALLBACK_AVAILABLE = False

try:
    from app.utils.redis_cache import redis_cache, cache_aside, cached_query, intelligent_cache
    REDIS_AVAILABLE = True
except ImportError:
    # Fallback quando não há Redis
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return self
    redis_cache = cache_aside = cached_query = intelligent_cache = Mock()
    REDIS_AVAILABLE = False

try:
    from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
    GRUPO_AVAILABLE = True
except ImportError:
    # Fallback quando não há Redis
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return self
    GrupoEmpresarialDetector = detectar_grupo_empresarial = Mock()
    GRUPO_AVAILABLE = False

try:
    from app.utils.ml_models_real import get_ml_models_system
    ML_MODELS_AVAILABLE = True
except ImportError:
    # Fallback quando não há Redis
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return self
    get_ml_models_system = Mock()
    ML_MODELS_AVAILABLE = False

try:
    from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
    CONFIG_AVAILABLE = True
except ImportError:
    # Fallback quando não há Redis
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return self
    ClaudeAIConfig = AdvancedConfig = Mock()
    CONFIG_AVAILABLE = False

try:
    from app.utils.api_helper import get_system_alerts
    API_HELPER_AVAILABLE = True
except ImportError:
    # Fallback quando não há Redis
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return self
    get_system_alerts = Mock()
    API_HELPER_AVAILABLE = False

try:
    from app.utils.ai_logging import ai_logger, AILogger
    AI_LOGGING_AVAILABLE = True
except ImportError:
    # Fallback quando não há Redis
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return self
    ai_logger = AILogger = Mock()
    AI_LOGGING_AVAILABLE = False

try:
    from app.financeiro.models import PendenciaFinanceiraNF
    FINANCEIRO_AVAILABLE = True
except ImportError:
    # Fallback quando não há Redis
    try:
        from unittest.mock import Mock
    except ImportError:
        class Mock:
            def __init__(self, *args, **kwargs):
                pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return self
    PendenciaFinanceiraNF = Mock
    FINANCEIRO_AVAILABLE = False

try:
    from sqlalchemy import func, and_, or_, text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    func, and_, or_, text = None
    SQLALCHEMY_AVAILABLE = False
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    func = and_ = or_ = text = None
    SQLALCHEMY_AVAILABLE = False
import json
import re
import time
import asyncio

# Configurar logger
logger = logging.getLogger(__name__)

class DataProvider:
    """
    Provedor de dados para o sistema Claude AI Novo.
    
    Responsável por fornecer dados estruturados para análise e processamento
    pelos diversos módulos do sistema.
    """
    
    @property
    def db(self):
        """Obtém db com fallback"""
        if FLASK_FALLBACK_AVAILABLE:
            return get_db()
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock()
    
    @property
    def Pedido(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("Pedido")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock

    @property
    def Embarque(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("Embarque")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock

    @property
    def EmbarqueItem(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("EmbarqueItem")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock

    @property
    def EntregaMonitorada(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("EntregaMonitorada")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock

    @property
    def RelatorioFaturamentoImportado(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("RelatorioFaturamentoImportado")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock

    @property
    def Transportadora(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("Transportadora")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock

    @property
    def Frete(self):
        if FLASK_FALLBACK_AVAILABLE:
            return get_model("Frete")
        else:
            # Fallback
            try:
                from unittest.mock import Mock
            except ImportError:
                class Mock:
                    def __init__(self, *args, **kwargs):
                        pass
                    def __call__(self, *args, **kwargs):
                        return self
                    def __getattr__(self, name):
                        return self
            return Mock

    def __init__(self, loader=None):
        """Inicializa o provedor de dados com LoaderManager opcional"""
        self.cache_timeout = 300  # 5 minutos
        self.logger = logging.getLogger(__name__)
        
        # LoaderManager injetado pelo Orchestrator
        self.loader = loader
        
        self.logger.info(f"{self.__class__.__name__} inicializado")
        if self.loader:
            self.logger.info('✅ DataProvider: LoaderManager disponível')
        else:
            self.logger.warning('⚠️ DataProvider: Sem LoaderManager, usando implementação direta')
    
    def set_loader(self, loader):
        """Configura LoaderManager após inicialização"""
        self.loader = loader
        self.logger.info('✅ LoaderManager configurado no DataProvider')
        
    def get_data_by_domain(self, domain: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Obtém dados por domínio específico.
        
        Args:
            domain: Domínio dos dados (entregas, pedidos, etc.)
            filters: Filtros opcionais
            
        Returns:
            Dict com dados do domínio
        """
        try:
            # SEMPRE usar LoaderManager quando disponível (arquitetura correta)
            if self.loader:
                self.logger.info(f"📊 DataProvider: Delegando para LoaderManager - domínio: {domain}")
                
                # Garantir que filters não seja None
                if filters is None:
                    filters = {}
                    
                # Adicionar filtros do contexto se necessário
                if 'cliente' in filters and 'cliente_especifico' not in filters:
                    filters['cliente_especifico'] = filters['cliente']
                
                result = self.loader.load_data_by_domain(domain, filters)
                
                # Se LoaderManager retornou dados válidos, usar
                if result and not result.get('erro'):
                    # Adicionar metadados
                    result['source'] = 'loader_manager'
                    result['optimized'] = True
                    self.logger.info(f"✅ LoaderManager retornou {result.get('total_registros', 0)} registros")
                    return result
                else:
                    self.logger.warning(f"⚠️ LoaderManager retornou erro ou sem dados: {result}")
            else:
                self.logger.warning("⚠️ LoaderManager não disponível no DataProvider")
            
            # Fallback APENAS se LoaderManager não disponível ou falhou
            self.logger.info(f"📊 DataProvider: Usando fallback para domínio: {domain}")
            
            if domain == "entregas":
                return self._get_entregas_data(filters)
            elif domain == "pedidos":
                return self._get_pedidos_data(filters)
            elif domain == "embarques":
                return self._get_embarques_data(filters)
            elif domain == "faturamento":
                return self._get_faturamento_data(filters)
            elif domain == "transportadoras":
                return self._get_transportadoras_data(filters)
            elif domain == "fretes":
                return self._get_fretes_data(filters)
            else:
                return {"error": f"Domínio '{domain}' não suportado"}
                
        except Exception as e:
            self.logger.error(f"Erro ao obter dados do domínio {domain}: {e}")
            return {"error": str(e), "domain": domain}
    
    def _get_entregas_data(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Obtém dados de entregas"""
        try:
            query = self.db.session.query(self.EntregaMonitorada)
            
            if filters:
                if filters.get("cliente"):
                    query = query.filter(EntregaMonitorada.cliente.ilike(f"%{filters['cliente']}%"))
                if filters.get("status"):
                    query = query.filter(EntregaMonitorada.status_finalizacao == filters["status"])
                if filters.get("data_inicio"):
                    query = query.filter(EntregaMonitorada.data_embarque >= filters["data_inicio"])
                if filters.get("data_fim"):
                    query = query.filter(EntregaMonitorada.data_embarque <= filters["data_fim"])
            
            entregas = query.limit(1000).all()
            
            return {
                "total": len(entregas),
                "data": [self._serialize_entrega(e) for e in entregas],
                "domain": "entregas"
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de entregas: {e}")
            return {"error": str(e)}
    
    def _get_pedidos_data(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Obtém dados de pedidos"""
        try:
            query = self.db.session.query(self.Pedido)
            
            if filters:
                if filters.get("cliente"):
                    query = query.filter(Pedido.cliente.ilike(f"%{filters['cliente']}%"))
                if filters.get("status"):
                    query = query.filter(Pedido.status == filters["status"])
                if filters.get("data_inicio"):
                    query = query.filter(Pedido.data_pedido >= filters["data_inicio"])
                if filters.get("data_fim"):
                    query = query.filter(Pedido.data_pedido <= filters["data_fim"])
            
            pedidos = query.limit(1000).all()
            
            return {
                "total": len(pedidos),
                "data": [self._serialize_pedido(p) for p in pedidos],
                "domain": "pedidos"
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de pedidos: {e}")
            return {"error": str(e)}
    
    def _get_embarques_data(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Obtém dados de embarques"""
        try:
            query = self.db.session.query(self.Embarque)
            
            if filters:
                if filters.get("status"):
                    query = query.filter(Embarque.status == filters["status"])
                if filters.get("data_inicio"):
                    query = query.filter(Embarque.data_embarque >= filters["data_inicio"])
                if filters.get("data_fim"):
                    query = query.filter(Embarque.data_embarque <= filters["data_fim"])
            
            embarques = query.limit(1000).all()
            
            return {
                "total": len(embarques),
                "data": [self._serialize_embarque(e) for e in embarques],
                "domain": "embarques"
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de embarques: {e}")
            return {"error": str(e)}
    
    def _get_faturamento_data(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Obtém dados de faturamento"""
        try:
            query = self.db.session.query(self.RelatorioFaturamentoImportado)
            
            if filters:
                if filters.get("cliente"):
                    query = query.filter(RelatorioFaturamentoImportado.nome_cliente.ilike(f"%{filters['cliente']}%"))
                if filters.get("data_inicio"):
                    query = query.filter(RelatorioFaturamentoImportado.data_fatura >= filters["data_inicio"])
                if filters.get("data_fim"):
                    query = query.filter(RelatorioFaturamentoImportado.data_fatura <= filters["data_fim"])
            
            faturamento = query.limit(1000).all()
            
            return {
                "total": len(faturamento),
                "data": [self._serialize_faturamento(f) for f in faturamento],
                "domain": "faturamento"
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de faturamento: {e}")
            return {"error": str(e)}
    
    def _get_transportadoras_data(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Obtém dados de transportadoras"""
        try:
            query = self.db.session.query(self.Transportadora)
            
            if filters:
                if filters.get("nome"):
                    query = query.filter(Transportadora.razao_social.ilike(f"%{filters['nome']}%"))
                if filters.get("cidade"):
                    query = query.filter(Transportadora.cidade.ilike(f"%{filters['cidade']}%"))
                if filters.get("uf"):
                    query = query.filter(Transportadora.uf == filters["uf"])
            
            transportadoras = query.limit(1000).all()
            
            return {
                "total": len(transportadoras),
                "data": [self._serialize_transportadora(t) for t in transportadoras],
                "domain": "transportadoras"
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de transportadoras: {e}")
            return {"error": str(e)}
    
    def _get_fretes_data(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Obtém dados de fretes"""
        try:
            query = self.db.session.query(self.Frete)
            
            if filters:
                if filters.get("transportadora"):
                    query = query.filter(Frete.transportadora.ilike(f"%{filters['transportadora']}%"))
                if filters.get("status"):
                    query = query.filter(Frete.status == filters["status"])
                if filters.get("data_inicio"):
                    query = query.filter(Frete.data_cotacao >= filters["data_inicio"])
                if filters.get("data_fim"):
                    query = query.filter(Frete.data_cotacao <= filters["data_fim"])
            
            fretes = query.limit(1000).all()
            
            return {
                "total": len(fretes),
                "data": [self._serialize_frete(f) for f in fretes],
                "domain": "fretes"
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de fretes: {e}")
            return {"error": str(e)}
    
    def _serialize_entrega(self, entrega) -> Dict[str, Any]:
        """Serializa uma entrega para dict"""
        return {
            "id": entrega.id,
            "cliente": entrega.cliente,
            "numero_nf": entrega.numero_nf,
            "municipio": entrega.municipio,
            "uf": entrega.uf,
            "destino": f"{entrega.municipio}/{entrega.uf}" if entrega.municipio and entrega.uf else None,
            "status": entrega.status_finalizacao,
            "data_embarque": entrega.data_embarque.isoformat() if entrega.data_embarque else None,
            "data_prevista": entrega.data_entrega_prevista.isoformat() if entrega.data_entrega_prevista else None,
            "data_realizada": entrega.data_hora_entrega_realizada.isoformat() if entrega.data_hora_entrega_realizada else None,
            "vendedor": entrega.vendedor,
            "transportadora": entrega.transportadora,
            "valor_nf": entrega.valor_nf,
            "entregue": entrega.entregue,
            "cnpj_cliente": entrega.cnpj_cliente
        }
    
    def _serialize_pedido(self, pedido) -> Dict[str, Any]:
        """Serializa um pedido para dict"""
        return {
            "id": pedido.id,
            "num_pedido": pedido.num_pedido,
            "cliente": pedido.cliente,
            "data_pedido": pedido.data_pedido.isoformat() if pedido.data_pedido else None,
            "valor_total": float(pedido.valor_total) if pedido.valor_total else None,
            "status": pedido.status,
            "vendedor": pedido.vendedor
        }
    
    def _serialize_embarque(self, embarque) -> Dict[str, Any]:
        """Serializa um embarque para dict"""
        return {
            "id": embarque.id,
            "numero": embarque.numero,
            "data_embarque": embarque.data_embarque.isoformat() if embarque.data_embarque else None,
            "destino": embarque.destino,
            "status": embarque.status,
            "valor_total": float(embarque.valor_total) if embarque.valor_total else None
        }
    
    def _serialize_faturamento(self, faturamento) -> Dict[str, Any]:
        """Serializa um faturamento para dict"""
        return {
            "id": faturamento.id,
            "numero_nf": faturamento.numero_nf,
            "nome_cliente": faturamento.nome_cliente,
            "data_fatura": faturamento.data_fatura.isoformat() if faturamento.data_fatura else None,
            "valor_total": float(faturamento.valor_total) if faturamento.valor_total else None,
            "origem": faturamento.origem,
            "incoterm": faturamento.incoterm
        }
    
    def _serialize_transportadora(self, transportadora) -> Dict[str, Any]:
        """Serializa uma transportadora para dict"""
        return {
            "id": transportadora.id,
            "razao_social": transportadora.razao_social,
            "cidade": transportadora.cidade,
            "uf": transportadora.uf,
            "cnpj": transportadora.cnpj,
            "freteiro": transportadora.freteiro if hasattr(transportadora, 'freteiro') else False
        }
    
    def _serialize_frete(self, frete) -> Dict[str, Any]:
        """Serializa um frete para dict"""
        return {
            "id": frete.id,
            "transportadora": frete.transportadora,
            "valor_cotado": float(frete.valor_cotado) if frete.valor_cotado else None,
            "valor_considerado": float(frete.valor_considerado) if frete.valor_considerado else None,
            "status": frete.status,
            "data_cotacao": frete.data_cotacao.isoformat() if frete.data_cotacao else None
        }


# Instância global para DataProvider
_data_provider = None

def get_data_provider(loader=None):
    """
    Retorna instância do DataProvider.
    
    Args:
        loader: LoaderManager opcional para injetar
        
    Returns:
        Instância do DataProvider
    """
    global _data_provider
    if _data_provider is None:
        # Tentar obter LoaderManager se não fornecido
        if loader is None:
            try:
                from app.claude_ai_novo.loaders import get_loader_manager
                loader = get_loader_manager()
                logger.info("✅ LoaderManager obtido automaticamente para DataProvider")
            except ImportError:
                logger.warning("⚠️ LoaderManager não disponível para DataProvider")
        
        _data_provider = DataProvider(loader=loader)
    return _data_provider 