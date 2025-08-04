"""
Pytest configuration and fixtures for MCP Logística tests
"""

import pytest
import os
import json
from datetime import datetime, date
from unittest.mock import Mock, MagicMock
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Import MCP components
from app.mcp_logistica import (
    MCPNLPEngine, EntityMapper, IntentClassifier, 
    QueryProcessor, PreferenceManager, ConfirmationSystem,
    ClaudeIntegration
)
from app.mcp_logistica.models import db as _db


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize extensions
    _db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    with app.app_context():
        _db.create_all()
        
    return app


@pytest.fixture(scope='function')
def db(app):
    """Create database for testing"""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Create Flask test client"""
    return app.test_client()


@pytest.fixture
def nlp_engine():
    """Create NLP engine instance"""
    return MCPNLPEngine()


@pytest.fixture
def entity_mapper(db):
    """Create entity mapper instance with database"""
    return EntityMapper(db.session)


@pytest.fixture
def intent_classifier():
    """Create intent classifier instance"""
    return IntentClassifier()


@pytest.fixture
def query_processor(db):
    """Create query processor instance"""
    return QueryProcessor(db.session)


@pytest.fixture
def preference_manager():
    """Create preference manager instance"""
    return PreferenceManager()


@pytest.fixture
def confirmation_system():
    """Create confirmation system instance"""
    return ConfirmationSystem()


@pytest.fixture
def claude_integration():
    """Create Claude integration instance (mocked)"""
    claude = ClaudeIntegration(api_key='test-key')
    claude.enabled = True
    claude.client = Mock()
    return claude


@pytest.fixture
def mock_user():
    """Create mock user for testing"""
    user = Mock()
    user.id = 1
    user.nome = "Test User"
    user.email = "test@example.com"
    user.is_authenticated = True
    return user


@pytest.fixture
def sample_queries():
    """Sample queries for testing"""
    return {
        'simple': "Quantas entregas temos hoje?",
        'with_entity': "Mostrar entregas da Empresa ABC",
        'with_temporal': "Listar pedidos de ontem",
        'with_location': "Entregas atrasadas em São Paulo",
        'complex': "Qual o status da NF 12345 do cliente XYZ?",
        'action': "Reagendar entrega da NF 789 para amanhã",
        'trend': "Tendência de entregas nos últimos 30 dias",
        'invalid': "askjdhaksjdh aksjdh"
    }


@pytest.fixture
def sample_entities():
    """Sample entities for testing"""
    return {
        'cliente': {
            'nome': 'Empresa ABC Ltda',
            'cnpj': '12.345.678/0001-90',
            'cidade': 'São Paulo',
            'uf': 'SP'
        },
        'entrega': {
            'numero_nf': '12345',
            'cliente': 'Empresa ABC Ltda',
            'data_entrega_prevista': date.today().isoformat(),
            'status': 'em_transito',
            'valor_nf': 1500.00
        },
        'pedido': {
            'num_pedido': 'PED-001',
            'raz_social_red': 'ABC',
            'data_pedido': date.today().isoformat(),
            'status': 'faturado'
        }
    }


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = Mock()
    session.query = Mock()
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def auth_headers(mock_user):
    """Create authentication headers"""
    return {
        'Authorization': 'Bearer test-token',
        'X-Session-Id': 'test-session-id'
    }


@pytest.fixture
def test_context():
    """Create test context"""
    return {
        'user_id': '1',
        'user_name': 'Test User',
        'timestamp': datetime.now().isoformat(),
        'session_id': 'test-session',
        'ip_address': '127.0.0.1',
        'user_agent': 'pytest'
    }


# Performance testing fixtures
@pytest.fixture
def performance_logger():
    """Logger for performance metrics"""
    import time
    
    class PerformanceLogger:
        def __init__(self):
            self.metrics = []
            
        def start(self, operation):
            return {
                'operation': operation,
                'start_time': time.time()
            }
            
        def end(self, context):
            end_time = time.time()
            duration = end_time - context['start_time']
            self.metrics.append({
                'operation': context['operation'],
                'duration': duration,
                'timestamp': datetime.now()
            })
            return duration
            
        def report(self):
            if not self.metrics:
                return "No metrics recorded"
                
            total_time = sum(m['duration'] for m in self.metrics)
            avg_time = total_time / len(self.metrics)
            
            return {
                'total_operations': len(self.metrics),
                'total_time': total_time,
                'average_time': avg_time,
                'operations': self.metrics
            }
            
    return PerformanceLogger()


# Mock data generators
@pytest.fixture
def generate_mock_entregas():
    """Generate mock delivery data"""
    def _generate(count=10):
        entregas = []
        for i in range(count):
            entregas.append({
                'id': i + 1,
                'numero_nf': f'{1000 + i}',
                'cliente': f'Cliente {i % 5}',
                'cnpj_cliente': f'12.345.{i:03d}/0001-00',
                'municipio': ['São Paulo', 'Rio de Janeiro', 'Belo Horizonte'][i % 3],
                'uf': ['SP', 'RJ', 'MG'][i % 3],
                'data_entrega_prevista': date.today().isoformat(),
                'entregue': i % 3 == 0,
                'valor_nf': 1000 + (i * 100)
            })
        return entregas
    return _generate


@pytest.fixture
def mock_claude_response():
    """Create mock Claude response"""
    def _response(response_type='direct', success=True):
        response = Mock()
        response.content = [Mock(text="Esta é uma resposta de teste do Claude.")]
        return response
    return _response