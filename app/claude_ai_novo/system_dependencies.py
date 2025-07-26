"""
Gerenciador de Dependências do Sistema - Claude AI Novo
======================================================

Este módulo centraliza o gerenciamento de dependências externas e do sistema antigo,
fornecendo fallbacks quando as dependências não estão disponíveis.
"""

import logging
from typing import Any, Dict, Optional, List
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

logger = logging.getLogger(__name__)

# Status das dependências
DEPENDENCIES_STATUS = {
    'flask': False,
    'sqlalchemy': False,
    'redis': False,
    'anthropic': False,
    'pandas': False,
    'openpyxl': False,
    'rapidfuzz': False,
    'nltk': False,
    'spacy': False,
    'psutil': False,
    'app_models': False,
    'app_auth': False,
}

# Verificar disponibilidade das dependências
try:
    import flask
    DEPENDENCIES_STATUS['flask'] = True
except ImportError:
    logger.warning("⚠️ Flask não disponível - usando mocks")

try:
    import sqlalchemy
    DEPENDENCIES_STATUS['sqlalchemy'] = True
except ImportError:
    logger.warning("⚠️ SQLAlchemy não disponível - usando mocks")

try:
    import redis
    DEPENDENCIES_STATUS['redis'] = True
except ImportError:
    logger.warning("⚠️ Redis não disponível - usando mocks")

try:
    import anthropic
    DEPENDENCIES_STATUS['anthropic'] = True
except ImportError:
    logger.warning("⚠️ Anthropic não disponível - usando mocks")

try:
    import pandas
    DEPENDENCIES_STATUS['pandas'] = True
except ImportError:
    logger.warning("⚠️ Pandas não disponível - usando mocks")

try:
    import openpyxl
    DEPENDENCIES_STATUS['openpyxl'] = True
except ImportError:
    logger.warning("⚠️ OpenPyXL não disponível - usando mocks")

try:
    import rapidfuzz
    DEPENDENCIES_STATUS['rapidfuzz'] = True
except ImportError:
    logger.warning("⚠️ RapidFuzz não disponível - usando mocks")

try:
    import nltk
    DEPENDENCIES_STATUS['nltk'] = True
except ImportError:
    logger.warning("⚠️ NLTK não disponível - usando mocks")

try:
    import spacy
    DEPENDENCIES_STATUS['spacy'] = True
except ImportError:
    logger.warning("⚠️ SpaCy não disponível - usando mocks")

try:
    import psutil
    DEPENDENCIES_STATUS['psutil'] = True
except ImportError:
    logger.warning("⚠️ PSUtil não disponível - usando mocks")

# Verificar módulos do sistema antigo
try:
    from app import models
    DEPENDENCIES_STATUS['app_models'] = True
except ImportError:
    logger.warning("⚠️ Modelos do sistema antigo não disponíveis")

try:
    from app.auth import models as auth_models
    DEPENDENCIES_STATUS['app_auth'] = True
except ImportError:
    logger.warning("⚠️ Modelos de autenticação não disponíveis")


class DependencyManager:
    """Gerencia dependências e fornece fallbacks"""
    
    @staticmethod
    def get_flask():
        """Retorna Flask ou mock"""
        if DEPENDENCIES_STATUS['flask']:
            import flask
            return flask
        else:
            # Mock do Flask
            class FlaskMock:
                Flask = Mock
                request = Mock()
                current_app = Mock()
                session = {}
                g = Mock()
                
                @staticmethod
                def jsonify(*args, **kwargs):
                    return {"data": args[0] if args else kwargs}
            
            return FlaskMock()
    
    @staticmethod
    def get_sqlalchemy():
        """Retorna SQLAlchemy ou mock"""
        if DEPENDENCIES_STATUS['sqlalchemy']:
            import sqlalchemy
            return sqlalchemy
        else:
            # Mock do SQLAlchemy
            class SQLAlchemyMock:
                create_engine = Mock(return_value=Mock())
                
                class orm:
                    sessionmaker = Mock(return_value=Mock())
                    Session = Mock()
                
                Column = Mock
                Integer = Mock
                String = Mock
                DateTime = Mock
                Boolean = Mock
                Text = Mock
                Float = Mock
                
                func = Mock()
                and_ = Mock()
                or_ = Mock()
                text = Mock()
            
            return SQLAlchemyMock()
    
    @staticmethod
    def get_redis():
        """Retorna Redis ou mock"""
        if DEPENDENCIES_STATUS['redis']:
            import redis
            return redis
        else:
            # Mock do Redis
            class RedisMock:
                class Redis:
                    def __init__(self, *args, **kwargs):
                        self._data = {}
                    
                    def get(self, key):
                        return self._data.get(key)
                    
                    def set(self, key, value, ex=None):
                        self._data[key] = value
                        return True
                    
                    def delete(self, key):
                        if key in self._data:
                            del self._data[key]
                        return 1
                    
                    def exists(self, key):
                        return key in self._data
            
            return RedisMock()
    
    @staticmethod
    def get_anthropic():
        """Retorna Anthropic ou mock"""
        if DEPENDENCIES_STATUS['anthropic']:
            import anthropic
            return anthropic
        else:
            # Mock do Anthropic
            class AnthropicMock:
                class Anthropic:
                    def __init__(self, *args, **kwargs):
                        pass
                    
                    class messages:
                        @staticmethod
                        def create(*args, **kwargs):
                            return Mock(
                                content=[Mock(text="Resposta mock do Claude")]
                            )
                
                class types:
                    MessageParam = dict
            
            return AnthropicMock()
    
    @staticmethod
    def get_pandas():
        """Retorna Pandas ou mock"""
        if DEPENDENCIES_STATUS['pandas']:
            import pandas
            return pandas
        else:
            # Mock do Pandas
            class PandasMock:
                DataFrame = Mock
                Series = Mock
                
                @staticmethod
                def read_sql(*args, **kwargs):
                    return Mock()
                
                @staticmethod
                def to_datetime(*args, **kwargs):
                    from datetime import datetime
                    return datetime.now()
            
            return PandasMock()
    
    @staticmethod
    def get_openpyxl():
        """Retorna OpenPyXL ou mock"""
        if DEPENDENCIES_STATUS['openpyxl']:
            import openpyxl
            return openpyxl
        else:
            # Mock do OpenPyXL
            class OpenPyXLMock:
                class Workbook:
                    def __init__(self):
                        self.active = Mock()
                    
                    def save(self, filename):
                        pass
                
                class styles:
                    Font = Mock
                    PatternFill = Mock
                    Alignment = Mock
                    Border = Mock
                    Side = Mock
                
                class utils:
                    @staticmethod
                    def get_column_letter(col):
                        return chr(64 + col)
            
            return OpenPyXLMock()
    
    @staticmethod
    def get_model_mock(model_name: str) -> Any:
        """Retorna mock para modelos do sistema antigo"""
        class ModelMock:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
                self.id = 1
                self.created_at = None
                self.updated_at = None
            
            @classmethod
            def query(cls):
                return Mock(
                    filter=Mock(return_value=Mock(
                        first=Mock(return_value=None),
                        all=Mock(return_value=[]),
                        count=Mock(return_value=0)
                    )),
                    all=Mock(return_value=[]),
                    first=Mock(return_value=None),
                    count=Mock(return_value=0)
                )
        
        ModelMock.__name__ = model_name
        return ModelMock
    
    @staticmethod
    def get_system_models() -> Dict[str, Any]:
        """Retorna mocks para todos os modelos do sistema"""
        models = {
            'Pedido': DependencyManager.get_model_mock('Pedido'),
            'Embarque': DependencyManager.get_model_mock('Embarque'),
            'EmbarqueItem': DependencyManager.get_model_mock('EmbarqueItem'),
            'Frete': DependencyManager.get_model_mock('Frete'),
            'EntregaMonitorada': DependencyManager.get_model_mock('EntregaMonitorada'),
            'AgendamentoEntrega': DependencyManager.get_model_mock('AgendamentoEntrega'),
            'Transportadora': DependencyManager.get_model_mock('Transportadora'),
            'Usuario': DependencyManager.get_model_mock('Usuario'),
            'RelatorioFaturamentoImportado': DependencyManager.get_model_mock('RelatorioFaturamentoImportado'),
            'DespesaExtra': DependencyManager.get_model_mock('DespesaExtra'),
            'PendenciaFinanceiraNF': DependencyManager.get_model_mock('PendenciaFinanceiraNF'),
        }
        return models
    
    @staticmethod
    def get_db_mock():
        """Retorna mock para o objeto db do Flask-SQLAlchemy"""
        class DBMock:
            session = Mock(
                query=Mock(return_value=Mock()),
                add=Mock(),
                commit=Mock(),
                rollback=Mock(),
                close=Mock()
            )
            
            @staticmethod
            def create_all():
                pass
        
        return DBMock()
    
    @staticmethod
    def get_current_user_mock():
        """Retorna mock para current_user do Flask-Login"""
        user = Mock()
        user.id = 1
        user.nome = "Usuário Mock"
        user.email = "mock@example.com"
        user.is_authenticated = True
        user.is_active = True
        user.is_anonymous = False
        return user


# Constantes úteis
UF_LIST = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']

# Funções auxiliares globais
def get_dependency_status() -> Dict[str, bool]:
    """Retorna status de todas as dependências"""
    return DEPENDENCIES_STATUS.copy()

def is_dependency_available(dependency: str) -> bool:
    """Verifica se uma dependência está disponível"""
    return DEPENDENCIES_STATUS.get(dependency, False)

def get_available_dependencies() -> List[str]:
    """Retorna lista de dependências disponíveis"""
    return [dep for dep, available in DEPENDENCIES_STATUS.items() if available]

def get_missing_dependencies() -> List[str]:
    """Retorna lista de dependências faltantes"""
    return [dep for dep, available in DEPENDENCIES_STATUS.items() if not available]


# Criar instância global
dependency_manager = DependencyManager()

# Exports convenientes
get_flask = dependency_manager.get_flask
get_sqlalchemy = dependency_manager.get_sqlalchemy
get_redis = dependency_manager.get_redis
get_anthropic = dependency_manager.get_anthropic
get_pandas = dependency_manager.get_pandas
get_openpyxl = dependency_manager.get_openpyxl
get_model_mock = dependency_manager.get_model_mock
get_system_models = dependency_manager.get_system_models
get_db_mock = dependency_manager.get_db_mock
get_current_user_mock = dependency_manager.get_current_user_mock