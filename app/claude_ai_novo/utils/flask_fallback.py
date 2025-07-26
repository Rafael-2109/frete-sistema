"""
🔄 FLASK FALLBACK - Fallback para Dependências Flask
==================================================

Módulo que fornece fallbacks para quando o Flask não está disponível,
permitindo que o sistema funcione em modo standalone.

Função: Substituir imports do Flask por mocks funcionais quando
o sistema é executado fora do contexto Flask.
"""

import logging
from typing import Dict, List, Any, Optional, Union
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

# Variáveis globais para indicar disponibilidade do Flask
try:
    from flask import Flask
    FLASK_AVAILABLE = True
except ImportError:
    Flask = None
    FLASK_AVAILABLE = False

class FlaskFallback:
    """
    Classe que simula funcionalidades do Flask quando não disponível.
    
    Permite que módulos que dependem do Flask funcionem em modo standalone
    para testes e execução independente.
    """
    
    def __init__(self):
        self.available = False
        self.mock_app = None
        self.mock_models = {}
        self._initialize_fallback()
    
    def _initialize_fallback(self):
        """Inicializa fallbacks do Flask"""
        try:
            # Tentar importar Flask
            import flask
            self.available = True
            logger.info("✅ Flask disponível - usando versão real")
            
        except ImportError:
            logger.warning("📦 Flask não disponível - usando fallback mock")
            self.available = False
            self._create_mock_flask()
    
    def _create_mock_flask(self):
        """Cria mocks do Flask"""
        # Mock do app Flask
        self.mock_app = Mock()
        self.mock_app.config = {
            'SECRET_KEY': 'mock-secret-key',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False
        }
        
        # Mock dos modelos principais
        self.mock_models = {
            'Pedido': self._create_mock_model('Pedido'),
            'Embarque': self._create_mock_model('Embarque'),
            'EmbarqueItem': self._create_mock_model('EmbarqueItem'),
            'EntregaMonitorada': self._create_mock_model('EntregaMonitorada'),
            'RelatorioFaturamentoImportado': self._create_mock_model('RelatorioFaturamentoImportado'),
            'Transportadora': self._create_mock_model('Transportadora'),
            'Usuario': self._create_mock_model('Usuario'),
            'Frete': self._create_mock_model('Frete'),
            'ContatoAgendamento': self._create_mock_model('ContatoAgendamento'),
            'Separacao': self._create_mock_model('Separacao'),
            'PendenciaFinanceira': self._create_mock_model('PendenciaFinanceira'),
            'ControlePortaria': self._create_mock_model('ControlePortaria'),
            'DespesaExtra': self._create_mock_model('DespesaExtra'),
            'Estoque': self._create_mock_model('Estoque'),
            'Produto': self._create_mock_model('Produto'),
            'ItemPedido': self._create_mock_model('ItemPedido')
        }
        
        logger.info("🔄 Mocks do Flask criados com sucesso")
    
    def _create_mock_model(self, model_name: str) -> Mock:
        """
        Cria mock de um modelo SQLAlchemy.
        
        Args:
            model_name: Nome do modelo
            
        Returns:
            Mock configurado do modelo
        """
        mock_model = Mock()
        mock_model.__name__ = model_name
        mock_model.__tablename__ = model_name.lower()
        
        # Mock query
        mock_query = Mock()
        mock_query.all.return_value = []
        mock_query.first.return_value = None
        mock_query.count.return_value = 0
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.join.return_value = mock_query
        
        mock_model.query = mock_query
        
        return mock_model
    
    def get_app(self):
        """
        Retorna app Flask ou mock.
        
        Returns:
            Flask app ou mock
        """
        if self.available:
            try:
                from flask import current_app
                return current_app
            except RuntimeError:
                # Fora do contexto Flask - tentar obter app real
                try:
                    # Tentar importar e criar app real
                    import sys
                    import os
                    
                    # Adicionar path do projeto se necessário
                    projeto_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    if projeto_path not in sys.path:
                        sys.path.insert(0, projeto_path)
                    
                    # Tentar importar o app real
                    from app import create_app
                    app = create_app()
                    
                    self.logger.info("✅ App Flask real obtido fora do contexto web")
                    return app
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Não foi possível obter app Flask real: {e}")
                    return self.mock_app
        else:
            return self.mock_app
    
    def get_model(self, model_name: str):
        """
        Retorna modelo real ou mock.
        
        Args:
            model_name: Nome do modelo
            
        Returns:
            Modelo real ou mock
        """
        if self.available:
            try:
                # CORREÇÃO: Verificar Flask context primeiro
                try:
                    from flask import current_app
                    current_app.config
                    
                    # Estamos em contexto Flask válido - importar modelos reais
                    if model_name == 'Pedido':
                        from app.pedidos.models import Pedido
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return Pedido
                    elif model_name == 'Embarque':
                        from app.embarques.models import Embarque
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return Embarque
                    elif model_name == 'EmbarqueItem':
                        from app.embarques.models import EmbarqueItem
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return EmbarqueItem
                    elif model_name == 'EntregaMonitorada':
                        from app.monitoramento.models import EntregaMonitorada
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return EntregaMonitorada
                    elif model_name == 'RelatorioFaturamentoImportado':
                        from app.faturamento.models import RelatorioFaturamentoImportado
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return RelatorioFaturamentoImportado
                    elif model_name == 'Transportadora':
                        from app.transportadoras.models import Transportadora
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return Transportadora
                    elif model_name == 'Usuario':
                        from app.auth.models import Usuario
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return Usuario
                    elif model_name == 'Frete':
                        from app.fretes.models import Frete
                        self.logger.info(f"✅ Modelo real {model_name} obtido")
                        return Frete
                    else:
                        # Modelo não mapeado - usar mock
                        self.logger.warning(f"⚠️ Modelo {model_name} não mapeado, usando mock")
                        return self.mock_models.get(model_name, Mock())
                        
                except RuntimeError:
                    # Fora do contexto Flask
                    self.logger.warning(f"⚠️ Fora do contexto Flask, usando mock para {model_name}")
                    return self.mock_models.get(model_name, Mock())
                    
            except ImportError:
                # Fallback para mock se import falhar
                self.logger.warning(f"⚠️ Import falhou para {model_name}, usando mock")
                return self.mock_models.get(model_name, Mock())
        else:
            return self.mock_models.get(model_name, Mock())
    
    def get_db(self):
        """
        Retorna instância do banco ou mock.
        
        Returns:
            SQLAlchemy db ou mock
        """
        if self.available:
            try:
                # CORREÇÃO: Primeiro verificar se estamos em Flask context válido
                try:
                    from flask import current_app
                    # Se current_app funciona, estamos em contexto Flask válido
                    current_app.config
                    
                    # Importar db real
                    from app import db
                    self.logger.info("✅ DB real obtido com sucesso")
                    return db
                    
                except RuntimeError:
                    # Não estamos em contexto Flask
                    self.logger.warning("⚠️ Fora do contexto Flask, usando mock DB")
                    return self._create_mock_db()
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Erro ao obter db real: {e}")
                return self._create_mock_db()
        else:
            return self._create_mock_db()
    
    def _create_mock_db(self):
        """Cria mock do banco de dados"""
        mock_db = Mock()
        mock_db.session = Mock()
        mock_db.session.query = Mock(return_value=Mock())
        mock_db.session.add = Mock()
        mock_db.session.commit = Mock()
        mock_db.session.rollback = Mock()
        mock_db.session.close = Mock()
        
        return mock_db
    
    def get_current_user(self):
        """
        Retorna usuário atual ou mock.
        
        Returns:
            Usuário atual ou mock
        """
        if self.available:
            try:
                from flask_login import current_user
                return current_user
            except ImportError:
                return self._create_mock_user()
        else:
            return self._create_mock_user()
    
    def _create_mock_user(self):
        """Cria mock do usuário"""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.nome = "Mock User"
        mock_user.email = "mock@test.com"
        mock_user.codigo_vendedor = "MOCK001"
        mock_user.perfil = "admin"
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.is_anonymous = False
        
        return mock_user
    
    def is_flask_available(self) -> bool:
        """
        Verifica se Flask está disponível.
        
        Returns:
            True se Flask está disponível
        """
        return self.available
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Obtém configuração do Flask ou padrão.
        
        Args:
            key: Chave da configuração
            default: Valor padrão
            
        Returns:
            Valor da configuração ou padrão
        """
        if self.available:
            try:
                from flask import current_app
                return current_app.config.get(key, default)
            except RuntimeError:
                return self.mock_app.config.get(key, default)
        else:
            return self.mock_app.config.get(key, default)

# Instância global
_flask_fallback = None

def get_flask_fallback() -> FlaskFallback:
    """
    Retorna instância global do FlaskFallback.
    
    Returns:
        FlaskFallback: Instância do fallback
    """
    global _flask_fallback
    if _flask_fallback is None:
        _flask_fallback = FlaskFallback()
    return _flask_fallback

# Funções de conveniência
def get_app():
    """Função de conveniência para obter app"""
    return get_flask_fallback().get_app()

def get_model(model_name: str):
    """Função de conveniência para obter modelo"""
    return get_flask_fallback().get_model(model_name)

def get_db():
    """Função de conveniência para obter db"""
    return get_flask_fallback().get_db()

def get_current_user():
    """Função de conveniência para obter usuário atual"""
    return get_flask_fallback().get_current_user()

def is_flask_available() -> bool:
    """Função de conveniência para verificar Flask"""
    return get_flask_fallback().is_flask_available()

def get_config(key: str, default: Any = None) -> Any:
    """Função de conveniência para obter configuração"""
    return get_flask_fallback().get_config(key, default)

# Exports
__all__ = [
    'FlaskFallback',
    'get_flask_fallback',
    'get_app',
    'get_model',
    'get_db',
    'get_current_user',
    'is_flask_available',
    'get_config'
] 