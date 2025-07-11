#!/usr/bin/env python3
"""
Base Processor - Módulo base comum para todos os processors
Centraliza imports, utilitários e padrões comuns
"""

# ==========================================
# IMPORTS ORGANIZADOS POR CATEGORIA
# ==========================================

# Standard Library
import os
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Third-party Libraries
import anthropic
from flask_login import current_user
from sqlalchemy import func, and_, or_, text

# Flask & Database
try:
    from flask import current_app
    from app import db
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    db = None

# Utilities
try:
    from app.utils.redis_cache import redis_cache, cache_aside, cached_query, intelligent_cache
    REDIS_CACHE_AVAILABLE = True
except ImportError:
    # Fallbacks para cache com interface compatível
    class FallbackCache:
        """Cache fallback que aceita qualquer parâmetro sem erros"""
        
        def get(self, key, default=None):
            return default
        
        def set(self, key, value, **kwargs):
            # Aceita qualquer parâmetro (ex, ttl, timeout, etc.)
            pass
        
        def delete(self, key):
            pass
        
        def exists(self, key):
            return False
        
        def expire(self, key, time):
            pass
    
    redis_cache = FallbackCache()
    cache_aside = lambda func: func  # Decorator sem efeito
    cached_query = lambda func: func  # Decorator sem efeito
    intelligent_cache = FallbackCache()
    REDIS_CACHE_AVAILABLE = False

try:
    from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
    GRUPO_EMPRESARIAL_AVAILABLE = True
except ImportError:
    # Fallbacks para grupo empresarial
    class FallbackGrupoDetector:
        def detectar(self, cnpj):
            return None
    
    detectar_grupo_empresarial = lambda cnpj: None
    GRUPO_EMPRESARIAL_AVAILABLE = False

try:
    from app.utils.ml_models_real import get_ml_models_system
    ML_MODELS_AVAILABLE = True
except ImportError:
    get_ml_models_system = lambda: None
    ML_MODELS_AVAILABLE = False

try:
    from app.utils.api_helper import get_system_alerts
    API_HELPER_AVAILABLE = True
except ImportError:
    get_system_alerts = lambda: []
    API_HELPER_AVAILABLE = False

try:
    from app.utils.ai_logging import ai_logger, AILogger
    AI_LOGGING_AVAILABLE = True
except ImportError:
    import logging
    ai_logger = logging.getLogger(__name__)
    AILogger = logging.Logger
    AI_LOGGING_AVAILABLE = False

UTILS_AVAILABLE = (
    REDIS_CACHE_AVAILABLE or 
    GRUPO_EMPRESARIAL_AVAILABLE or 
    ML_MODELS_AVAILABLE or 
    API_HELPER_AVAILABLE or 
    AI_LOGGING_AVAILABLE
)

# Configuration
try:
    from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Models (imports mais comuns)
try:
    from app.fretes.models import Frete, DespesaExtra
    from app.embarques.models import Embarque, EmbarqueItem
    from app.transportadoras.models import Transportadora
    from app.pedidos.models import Pedido
    from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
    from app.faturamento.models import RelatorioFaturamentoImportado
    from app.financeiro.models import PendenciaFinanceiraNF
    MODELS_AVAILABLE = True
except ImportError:
    # Fallbacks para models quando não disponíveis
    class FallbackModel:
        def __init__(self):
            self.id = None
        
        def __repr__(self):
            return f"<FallbackModel>"
    
    Frete = FallbackModel
    DespesaExtra = FallbackModel
    Embarque = FallbackModel
    EmbarqueItem = FallbackModel
    Transportadora = FallbackModel
    Pedido = FallbackModel
    EntregaMonitorada = FallbackModel
    AgendamentoEntrega = FallbackModel
    RelatorioFaturamentoImportado = FallbackModel
    PendenciaFinanceiraNF = FallbackModel
    MODELS_AVAILABLE = False

# ==========================================
# CONFIGURAÇÃO DE LOGGING
# ==========================================

logger = logging.getLogger(__name__)

# ==========================================
# CLASSES BASE COMUNS
# ==========================================

class BaseOrchestrator:
    """
    Classe base para todos os orquestradores
    
    Fornece funcionalidades comuns:
    - Coordenação de componentes
    - Gerenciamento de estado
    - Logging padronizado
    - Tratamento de erros
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.components = {}
        self.status = 'initialized'
        self.initialized = True
        self.logger.debug(f"{self.__class__.__name__} inicializado")
    
    def register_component(self, name: str, component: Any) -> None:
        """Registra um componente no orquestrador"""
        self.components[name] = component
        self.logger.debug(f"Componente '{name}' registrado")
    
    def get_component(self, name: str) -> Optional[Any]:
        """Obtém um componente registrado"""
        return self.components.get(name)
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do orquestrador"""
        return {
            'orchestrator': self.__class__.__name__,
            'status': self.status,
            'components_count': len(self.components),
            'components': list(self.components.keys()),
            'initialized': self.initialized,
            'timestamp': datetime.now().isoformat()
        }
    
    def health_check(self) -> bool:
        """Verifica se o orquestrador está funcionando"""
        return self.initialized and self.status == 'initialized'

class BaseProcessor:
    """
    Classe base para todos os processors
    
    Fornece funcionalidades comuns:
    - Validação de entrada
    - Logging padronizado
    - Tratamento de erros
    - Cache inteligente
    - Formatação de dados
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.initialized = False
        self._init_processor()
    
    def _init_processor(self):
        """Inicialização comum do processor"""
        try:
            # Verificar dependências
            self._check_dependencies()
            
            # Configurar cache se disponível
            if UTILS_AVAILABLE:
                self.cache = intelligent_cache
            else:
                self.cache = None
            
            self.initialized = True
            self.logger.debug(f"{self.__class__.__name__} inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro na inicialização: {e}")
            raise
    
    def _check_dependencies(self):
        """Verifica se dependências estão disponíveis"""
        dependencies = {
            'Flask': FLASK_AVAILABLE,
            'Utils': UTILS_AVAILABLE,
            'Config': CONFIG_AVAILABLE,
            'Models': MODELS_AVAILABLE
        }
        
        missing = [name for name, available in dependencies.items() if not available]
        
        if missing:
            self.logger.warning(f"Dependências não disponíveis: {', '.join(missing)}")
        
        return len(missing) == 0
    
    def _validate_input(self, data: Any, required_type: type = str) -> bool:
        """Valida entrada de dados"""
        if data is None:
            return False
        
        if not isinstance(data, required_type):
            return False
        
        if isinstance(data, str) and not data.strip():
            return False
        
        return True
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitiza entrada de texto"""
        if not isinstance(text, str):
            return ""
        
        # Remover caracteres especiais perigosos
        import re
        sanitized = re.sub(r'[<>"\']', '', text)
        
        # Limitar tamanho
        return sanitized.strip()[:1000]
    
    def _log_operation(self, operation: str, data: Any = None, level: str = "info"):
        """Log padronizado de operações"""
        
        if not self.logger:
            return
        
        message = f"🔄 {operation}"
        if data:
            message += f" | Data: {str(data)[:100]}"
        
        getattr(self.logger, level.lower())(message)
    
    def _handle_error(self, error: Exception, operation: str, context: str = "") -> str:
        """Tratamento padronizado de erros"""
        
        error_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(error)) % 10000:04d}"
        
        error_msg = f"❌ Erro em {operation} (ID: {error_id})"
        if context:
            error_msg += f" | Contexto: {context}"
        
        self.logger.error(f"{error_msg} | Erro: {str(error)}")
        
        return f"⚠️ **Erro interno** (ID: {error_id})\n\nOperação: {operation}\n\nPor favor, tente novamente ou entre em contato com suporte."
    
    def _get_cached_result(self, cache_key: str, ttl: int = 300) -> Optional[Any]:
        """Recupera resultado do cache se disponível"""
        
        if not self.cache or not UTILS_AVAILABLE:
            return None
        
        try:
            return self.cache.get(cache_key)
        except Exception as e:
            self.logger.warning(f"Erro no cache (get): {e}")
            return None
    
    def _set_cached_result(self, cache_key: str, result: Any, ttl: int = 300):
        """Armazena resultado no cache se disponível"""
        
        if not self.cache:
            return
        
        # Wrapper seguro para evitar erros de tipos
        def _safe_cache_set(cache_obj, key: str, value: Any, expire_time: int = 300):
            """Wrapper seguro para cache.set que tenta diferentes assinaturas"""
            try:
                # Para Redis real
                if hasattr(cache_obj, 'set') and callable(cache_obj.set):
                    # Tentar diferentes assinaturas
                    cache_set_method = getattr(cache_obj, 'set')
                    
                    # Método 1: Redis style com ex
                    try:
                        cache_set_method(key, value, ex=expire_time)
                        return True
                    except:
                        pass
                    
                    # Método 2: Simples sem parâmetros
                    try:
                        cache_set_method(key, value)
                        return True
                    except:
                        pass
                    
                    # Método 3: Com timeout
                    try:
                        cache_set_method(key, value, timeout=expire_time)
                        return True
                    except:
                        pass
                
                return False
            except:
                return False
        
        # Usar o wrapper seguro
        try:
            success = _safe_cache_set(self.cache, cache_key, result, ttl)
            if not success and hasattr(self, 'logger'):
                self.logger.debug("Cache set não conseguiu usar nenhuma assinatura compatível")
        except Exception as e:
            # Cache é opcional - falha silenciosa
            if hasattr(self, 'logger'):
                self.logger.debug(f"Erro no cache (ignorado): {e}")
            pass
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Gera chave de cache consistente"""
        
        import hashlib
        
        # Concatenar argumentos
        key_data = f"{prefix}::{':'.join(str(arg) for arg in args)}"
        
        # Hash para garantir tamanho consistente
        return f"proc_{hashlib.md5(key_data.encode()).hexdigest()[:12]}"
    
    def _format_date_br(self, date_obj: Any) -> str:
        """Formata data em formato brasileiro"""
        
        if not date_obj:
            return ""
        
        try:
            if isinstance(date_obj, str):
                return date_obj
            
            if hasattr(date_obj, 'strftime'):
                return date_obj.strftime('%d/%m/%Y')
            
            return str(date_obj)
            
        except Exception:
            return ""
    
    def _format_currency(self, value: Union[int, float]) -> str:
        """Formata valor monetário"""
        
        try:
            if value is None:
                return "R$ 0,00"
            
            return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
        except Exception:
            return "R$ 0,00"
    
    def _format_weight(self, weight: Union[int, float]) -> str:
        """Formata peso"""
        
        try:
            if weight is None:
                return "0 kg"
            
            return f"{float(weight):,.1f} kg".replace(',', 'X').replace('.', ',').replace('X', '.')
            
        except Exception:
            return "0 kg"
    
    def _format_percentage(self, value: Union[int, float]) -> str:
        """Formata porcentagem"""
        
        try:
            if value is None:
                return "0%"
            
            return f"{float(value):.1f}%"
            
        except Exception:
            return "0%"
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do processor"""
        
        return {
            'processor': self.__class__.__name__,
            'initialized': self.initialized,
            'dependencies': {
                'flask': FLASK_AVAILABLE,
                'utils': UTILS_AVAILABLE,
                'config': CONFIG_AVAILABLE,
                'models': MODELS_AVAILABLE
            },
            'cache_available': self.cache is not None,
            'timestamp': datetime.now().isoformat()
        }
    
    def health_check(self) -> bool:
        """Verifica se o processor está funcionando"""
        
        if not self.initialized:
            return False
        
        # Verificar dependências críticas
        if not FLASK_AVAILABLE or not db:
            return False
        
        return True

# ==========================================
# UTILITIES COMUNS
# ==========================================

def format_response_advanced(content: str, source: str = "Processor", metadata: Optional[Dict] = None) -> str:
    """Formata resposta com metadados avançados"""
    
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    response = content
    
    if metadata:
        response += f"\n\n---\n🤖 **{source}**"
        response += f"\n🕒 **Timestamp:** {timestamp}"
        
        if metadata.get('cache_hit'):
            response += f"\n⚡ **Cache:** Hit"
        
        if metadata.get('processing_time'):
            response += f"\n⏱️ **Tempo:** {metadata['processing_time']:.2f}s"
    
    return response

def create_processor_summary(data: List[Any], processor_type: str) -> Dict[str, Any]:
    """Cria resumo estatístico de dados processados"""
    
    if not data:
        return {'total': 0, 'type': processor_type}
    
    summary = {
        'total': len(data),
        'type': processor_type,
        'timestamp': datetime.now().isoformat(),
        'first_item': str(data[0])[:100] if data else None,
        'sample_size': min(len(data), 5)
    }
    
    return summary

# ==========================================
# INSTÂNCIAS GLOBAIS DE CONVENIÊNCIA
# ==========================================

# Instância base para reutilização
_base_processor = None

def get_base_processor() -> BaseProcessor:
    """Retorna instância base do processor"""
    global _base_processor
    if _base_processor is None:
        _base_processor = BaseProcessor()
    return _base_processor

# ==========================================
# EXPORTS ORGANIZADOS
# ==========================================

__all__ = [
    # Classes base
    'BaseProcessor',
    'BaseOrchestrator',
    
    # Utilities
    'format_response_advanced',
    'create_processor_summary', 
    'get_base_processor',
    
    # Imports centralizados (para re-export)
    'logging', 'datetime', 'db', 'current_user',
    'func', 'and_', 'or_', 'text',
    
    # Cache utilities
    'redis_cache', 'cache_aside', 'cached_query', 'intelligent_cache',
    
    # Outros utilities
    'detectar_grupo_empresarial', 'get_ml_models_system',
    'get_system_alerts', 'ai_logger', 'AILogger',
    
    # Models
    'Frete', 'DespesaExtra', 'Embarque', 'EmbarqueItem', 'Transportadora',
    'Pedido', 'EntregaMonitorada', 'AgendamentoEntrega',
    'RelatorioFaturamentoImportado', 'PendenciaFinanceiraNF',
    
    # Flags de disponibilidade
    'FLASK_AVAILABLE', 'UTILS_AVAILABLE', 'CONFIG_AVAILABLE', 'MODELS_AVAILABLE'
] 