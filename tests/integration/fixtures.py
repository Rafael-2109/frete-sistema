"""
Test fixtures and factories for integration tests
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import aiohttp
from fastapi.testclient import TestClient
from flask import Flask
from flask.testing import FlaskClient
import jwt
from cryptography.fernet import Fernet


# Database fixtures
@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine"""
    engine = create_engine("sqlite:///:memory:")
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for tests"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def async_db_engine():
    """Create async test database engine"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return engine


@pytest.fixture(scope="function")
async def async_db_session(async_db_engine):
    """Create async database session for tests"""
    async with AsyncSession(async_db_engine) as session:
        yield session
        await session.rollback()


# FastAPI client fixtures
@pytest.fixture(scope="function")
def client(mock_mcp_service):
    """Create FastAPI test client"""
    from app.mcp_sistema.api import create_app
    
    app = create_app()
    # Override dependencies
    app.dependency_overrides[get_mcp_service] = lambda: mock_mcp_service
    
    with TestClient(app) as client:
        yield client


# Flask client fixtures
@pytest.fixture(scope="function")
def flask_app(mock_portfolio_bridge):
    """Create Flask test application"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    
    # Register blueprints
    from app.api.routes.portfolio_mcp import portfolio_mcp_bp
    app.register_blueprint(portfolio_mcp_bp)
    
    # Mock portfolio bridge
    with app.app_context():
        app.portfolio_bridge = mock_portfolio_bridge
    
    return app


@pytest.fixture(scope="function")
def flask_client(flask_app):
    """Create Flask test client"""
    return flask_app.test_client()


# WebSocket client fixtures
@pytest.fixture(scope="function")
async def websocket_client():
    """Create WebSocket test client"""
    async def websocket_connect(path):
        session = aiohttp.ClientSession()
        ws = await session.ws_connect(f"ws://localhost:8000{path}")
        yield ws
        await ws.close()
        await session.close()
    
    return websocket_connect


# Authentication fixtures
@pytest.fixture(scope="function")
def auth_headers():
    """Create authenticated request headers"""
    token = jwt.encode(
        {
            "sub": "user_123",
            "roles": ["freight_manager"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        },
        "test-secret-key",
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def encryption_key():
    """Generate test encryption key"""
    return Fernet.generate_key()


# Mock service fixtures
@pytest.fixture(scope="function")
def mock_mcp_service():
    """Create mock MCP service"""
    service = AsyncMock()
    service.list_tools = AsyncMock(return_value=[])
    service.execute_tool = AsyncMock(return_value={})
    service.list_resources = AsyncMock(return_value=[])
    service.read_resource = AsyncMock(return_value={})
    service.process_natural_language = AsyncMock(return_value={})
    service.execute_batch = AsyncMock(return_value=[])
    service.list_prompts = AsyncMock(return_value=[])
    service.execute_prompt = AsyncMock(return_value={})
    service.retry_failed_operations = AsyncMock(return_value=[])
    service.execute_streaming = AsyncMock()
    return service


@pytest.fixture(scope="function")
def mock_portfolio_bridge():
    """Create mock portfolio bridge"""
    bridge = MagicMock()
    bridge.get_status = MagicMock(return_value={"status": "healthy"})
    bridge.process_natural_language_query = MagicMock(return_value={})
    bridge.get_analytics = MagicMock(return_value={})
    bridge.setup_monitoring = MagicMock(return_value={})
    bridge.execute_batch_operation = MagicMock(return_value={})
    bridge.intelligent_search = MagicMock(return_value={})
    bridge.export_with_analysis = MagicMock(return_value={})
    bridge.detect_anomalies = MagicMock(return_value={})
    bridge.execute_workflow = MagicMock(return_value={})
    bridge.subscribe_to_updates = MagicMock(return_value={})
    bridge.create_order = MagicMock(return_value={})
    bridge.create_batch_orders = MagicMock(return_value={})
    bridge.update_order_status = MagicMock(return_value={})
    bridge.get_order_details = MagicMock(return_value={})
    bridge.get_historical_data = MagicMock(return_value={})
    bridge.create_workflow = MagicMock(return_value={})
    bridge.get_workflow_status = MagicMock(return_value={})
    bridge.log_customer_interaction = MagicMock(return_value={})
    bridge.create_action_plan = MagicMock(return_value={})
    bridge.setup_predictive_monitoring = MagicMock(return_value={})
    bridge.check_workspace_permission = MagicMock(return_value=True)
    bridge.check_order_permission = MagicMock(return_value=True)
    bridge.verify_rollback = MagicMock(return_value={})
    return bridge


@pytest.fixture(scope="function")
def mock_auth_service():
    """Create mock authentication service"""
    service = AsyncMock()
    service.authenticate = AsyncMock(return_value={})
    service.generate_tokens = AsyncMock(return_value={})
    service.validate_token = AsyncMock(return_value=({"id": "user_123"}, ["freight:read"]))
    service.create_api_key = AsyncMock(return_value={})
    service.authorize_client = AsyncMock(return_value={})
    service.exchange_code = AsyncMock(return_value={})
    return service


# Data factory functions
class DataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_order(order_id=None, **kwargs):
        """Create test order data"""
        base_order = {
            "order_id": order_id or f"ORD-{datetime.utcnow().timestamp()}",
            "customer_id": "CUST-001",
            "status": "pending",
            "total_value": 1000.00,
            "freight_cost": 100.00,
            "created_at": datetime.utcnow().isoformat(),
            "items": [
                {"sku": "ITEM-001", "quantity": 5, "unit_price": 200.00}
            ]
        }
        base_order.update(kwargs)
        return base_order
    
    @staticmethod
    def create_freight_request(**kwargs):
        """Create freight calculation request"""
        base_request = {
            "origin": {
                "city": "São Paulo",
                "state": "SP",
                "cep": "01310-100"
            },
            "destination": {
                "city": "Rio de Janeiro",
                "state": "RJ",
                "cep": "20040-020"
            },
            "package": {
                "weight": 1000,
                "dimensions": {"length": 100, "width": 50, "height": 50},
                "value": 5000.00
            },
            "service": "express"
        }
        
        # Deep update with kwargs
        def deep_update(base, update):
            for key, value in update.items():
                if isinstance(value, dict) and key in base:
                    deep_update(base[key], value)
                else:
                    base[key] = value
        
        deep_update(base_request, kwargs)
        return base_request
    
    @staticmethod
    def create_user(**kwargs):
        """Create test user data"""
        base_user = {
            "id": f"user_{datetime.utcnow().timestamp()}",
            "email": "test@example.com",
            "name": "Test User",
            "roles": ["freight_user"],
            "permissions": ["freight:read"],
            "active": True
        }
        base_user.update(kwargs)
        return base_user
    
    @staticmethod
    def create_api_response(success=True, **kwargs):
        """Create standardized API response"""
        base_response = {
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": f"req_{datetime.utcnow().timestamp()}"
        }
        
        if success:
            base_response["data"] = kwargs.get("data", {})
        else:
            base_response["error"] = kwargs.get("error", "Unknown error")
            base_response["error_code"] = kwargs.get("error_code", "UNKNOWN_ERROR")
        
        base_response.update(kwargs)
        return base_response


@pytest.fixture(scope="function")
def data_factory():
    """Provide data factory for tests"""
    return DataFactory()


# Performance testing fixtures
@pytest.fixture(scope="function")
def performance_monitor():
    """Monitor test performance"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.measurements = {}
        
        def start(self, name):
            self.measurements[name] = {"start": time.perf_counter()}
        
        def stop(self, name):
            if name in self.measurements:
                end_time = time.perf_counter()
                self.measurements[name]["end"] = end_time
                self.measurements[name]["duration"] = (
                    end_time - self.measurements[name]["start"]
                )
        
        def assert_performance(self, name, max_duration):
            """Assert operation completed within time limit"""
            duration = self.measurements.get(name, {}).get("duration", float("inf"))
            assert duration < max_duration, (
                f"Operation '{name}' took {duration:.3f}s, "
                f"exceeding limit of {max_duration}s"
            )
        
        def get_report(self):
            """Get performance report"""
            return {
                name: {
                    "duration": data.get("duration", None),
                    "status": "completed" if "duration" in data else "running"
                }
                for name, data in self.measurements.items()
            }
    
    return PerformanceMonitor()


# Async helpers
@pytest.fixture(scope="function")
def async_runner():
    """Helper to run async functions in sync tests"""
    def run(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return run


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Add any cleanup code here


# Export fixtures
__all__ = [
    "db_engine",
    "db_session",
    "async_db_engine", 
    "async_db_session",
    "client",
    "flask_app",
    "flask_client",
    "websocket_client",
    "auth_headers",
    "encryption_key",
    "mock_mcp_service",
    "mock_portfolio_bridge",
    "mock_auth_service",
    "data_factory",
    "performance_monitor",
    "async_runner",
    "DataFactory"
]