"""
Pytest configuration and shared fixtures for MCP Sistema tests
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Generator
from unittest.mock import Mock, AsyncMock, patch
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import app components
from app.mcp_sistema.main import app
from app.mcp_sistema.models.database import Base, get_db
from app.mcp_sistema.services.auth.jwt_service import JWTService
from app.mcp_sistema.models.user import User
from app.mcp_sistema.models.mcp_models import QueryLog, EntityMapping, UserPreference


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a clean database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def jwt_service() -> JWTService:
    """Create a JWT service instance for testing"""
    return JWTService(
        secret_key="test-secret-key",
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )


@pytest.fixture
def auth_headers(jwt_service: JWTService) -> Dict[str, str]:
    """Generate authentication headers with a valid token"""
    token = jwt_service.create_access_token({"sub": "test-user", "user_id": 1})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user"""
    user = User(
        username="test_user",
        email="test@example.com",
        is_active=True,
        created_at=datetime.utcnow()
    )
    user.set_password("test_password123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_queries_pt_br() -> List[Dict[str, Any]]:
    """Sample queries in Brazilian Portuguese for testing"""
    return [
        {
            "query": "quero criar um embarque para São Paulo",
            "intent": "create_shipment",
            "entities": {
                "action": "criar",
                "object": "embarque",
                "destination": "São Paulo"
            }
        },
        {
            "query": "qual o status do frete 12345",
            "intent": "check_freight_status",
            "entities": {
                "action": "verificar",
                "object": "frete",
                "freight_id": "12345"
            }
        },
        {
            "query": "aprovar todos os fretes pendentes do cliente XYZ",
            "intent": "approve_freights",
            "entities": {
                "action": "aprovar",
                "object": "fretes",
                "status": "pendentes",
                "client": "XYZ"
            }
        },
        {
            "query": "gerar relatório de entregas do mês passado",
            "intent": "generate_report",
            "entities": {
                "action": "gerar",
                "object": "relatório",
                "type": "entregas",
                "period": "mês passado"
            }
        },
        {
            "query": "quanto foi faturado hoje",
            "intent": "check_revenue",
            "entities": {
                "action": "verificar",
                "metric": "faturamento",
                "period": "hoje"
            }
        }
    ]


@pytest.fixture
def entity_mappings(db_session: Session) -> List[EntityMapping]:
    """Create test entity mappings"""
    mappings = [
        EntityMapping(
            entity_type="action",
            entity_value="criar",
            mapped_value="create",
            confidence=0.95
        ),
        EntityMapping(
            entity_type="action",
            entity_value="aprovar",
            mapped_value="approve",
            confidence=0.98
        ),
        EntityMapping(
            entity_type="object",
            entity_value="embarque",
            mapped_value="shipment",
            confidence=0.97
        ),
        EntityMapping(
            entity_type="object",
            entity_value="frete",
            mapped_value="freight",
            confidence=0.96
        ),
        EntityMapping(
            entity_type="location",
            entity_value="são paulo",
            mapped_value="SAO_PAULO",
            confidence=0.99
        )
    ]
    
    for mapping in mappings:
        db_session.add(mapping)
    db_session.commit()
    
    return mappings


@pytest.fixture
def mock_database_data() -> Dict[str, List[Dict[str, Any]]]:
    """Mock database data for testing"""
    return {
        "embarques": [
            {
                "id": 1,
                "numero": "EMB001",
                "cliente": "Cliente A",
                "destino": "São Paulo",
                "status": "em_transito",
                "created_at": datetime.utcnow()
            },
            {
                "id": 2,
                "numero": "EMB002",
                "cliente": "Cliente B",
                "destino": "Rio de Janeiro",
                "status": "entregue",
                "created_at": datetime.utcnow() - timedelta(days=1)
            }
        ],
        "fretes": [
            {
                "id": 1,
                "numero": "FRT12345",
                "valor": 1500.00,
                "status": "pendente",
                "cliente_id": 1,
                "embarque_id": 1
            },
            {
                "id": 2,
                "numero": "FRT12346",
                "valor": 2300.00,
                "status": "aprovado",
                "cliente_id": 2,
                "embarque_id": 2
            }
        ],
        "clientes": [
            {
                "id": 1,
                "nome": "Cliente A",
                "cnpj": "12345678901234",
                "email": "clientea@example.com"
            },
            {
                "id": 2,
                "nome": "Cliente B",
                "cnpj": "98765432109876",
                "email": "clienteb@example.com"
            }
        ]
    }


@pytest.fixture
def user_preferences(db_session: Session, test_user: User) -> List[UserPreference]:
    """Create test user preferences"""
    preferences = [
        UserPreference(
            user_id=test_user.id,
            preference_key="language",
            preference_value="pt-BR"
        ),
        UserPreference(
            user_id=test_user.id,
            preference_key="default_view",
            preference_value="dashboard"
        ),
        UserPreference(
            user_id=test_user.id,
            preference_key="notifications",
            preference_value="enabled"
        )
    ]
    
    for pref in preferences:
        db_session.add(pref)
    db_session.commit()
    
    return preferences


@pytest.fixture
def mock_nlp_service():
    """Mock NLP service for testing"""
    mock = Mock()
    mock.process_query = AsyncMock(return_value={
        "intent": "check_status",
        "entities": {"object": "frete", "id": "12345"},
        "confidence": 0.92
    })
    mock.train_model = AsyncMock(return_value={"status": "success"})
    return mock


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.delete = AsyncMock(return_value=True)
    mock.expire = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def performance_metrics() -> Dict[str, Any]:
    """Performance benchmark thresholds"""
    return {
        "api_response_time_ms": 100,  # Max 100ms for API responses
        "nlp_processing_time_ms": 50,  # Max 50ms for NLP processing
        "db_query_time_ms": 20,  # Max 20ms for database queries
        "cache_hit_ratio": 0.8,  # Minimum 80% cache hit ratio
        "concurrent_requests": 100,  # Handle 100 concurrent requests
        "memory_usage_mb": 512  # Max 512MB memory usage
    }