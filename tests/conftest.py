"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, Mock
import tempfile
import shutil
from datetime import datetime
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Global test configuration
@pytest.fixture(scope="session")
def test_config():
    """Global test configuration"""
    return {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/15",
        "jwt_secret": "test-secret-key",
        "encryption_key": "test-encryption-key",
        "rate_limit_enabled": False,  # Disable for most tests
        "cache_enabled": False,  # Disable for most tests
    }


# Mock Redis client
@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = -1
    redis_mock.incr.return_value = 1
    redis_mock.pipeline.return_value = MagicMock()
    return redis_mock


# Mock database session
@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.query.return_value = MagicMock()
    session.add.return_value = None
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    return session


# Temporary directory for file operations
@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


# Sample freight data
@pytest.fixture
def sample_freight_data():
    """Sample freight calculation data"""
    return {
        "origin": {
            "city": "São Paulo",
            "state": "SP",
            "cep": "01310-100",
            "coordinates": {"lat": -23.5505, "lng": -46.6333}
        },
        "destination": {
            "city": "Rio de Janeiro",
            "state": "RJ", 
            "cep": "20040-020",
            "coordinates": {"lat": -22.9068, "lng": -43.1729}
        },
        "package": {
            "weight": 1000,  # kg
            "dimensions": {"length": 100, "width": 50, "height": 50},  # cm
            "value": 5000.00,  # BRL
            "fragile": False
        },
        "service": "express",
        "expected_cost": 250.00,
        "expected_days": 2
    }


# Mock MCP server
@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing"""
    server = MagicMock()
    
    # Mock tool responses
    server.process_request.return_value = {
        "result": {"success": True},
        "error": None
    }
    
    # Mock authentication
    server.authenticate.return_value = {
        "token": "test-token-123",
        "expires_at": datetime.utcnow().isoformat()
    }
    
    return server


# Test user data
@pytest.fixture
def test_user():
    """Test user data"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["freight_manager", "admin"],
        "permissions": ["freight:read", "freight:write", "users:manage"],
        "active": True,
        "created_at": datetime.utcnow().isoformat()
    }


# Mock neural model
@pytest.fixture
def mock_neural_model():
    """Mock neural processing model"""
    model = MagicMock()
    
    # Mock predictions
    model.predict.return_value = {
        "intent": "calculate_freight",
        "confidence": 0.95,
        "entities": {
            "origin": "São Paulo",
            "destination": "Rio de Janeiro",
            "weight": 1000
        }
    }
    
    # Mock training
    model.train.return_value = {
        "epochs": 10,
        "loss": 0.05,
        "accuracy": 0.95
    }
    
    return model


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Setup test environment variables"""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")


# Async support
@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Performance tracking
@pytest.fixture
def performance_tracker():
    """Track test performance"""
    import time
    
    class PerformanceTracker:
        def __init__(self):
            self.measurements = {}
        
        def start(self, name):
            self.measurements[name] = {"start": time.time()}
        
        def stop(self, name):
            if name in self.measurements:
                self.measurements[name]["end"] = time.time()
                self.measurements[name]["duration"] = (
                    self.measurements[name]["end"] - 
                    self.measurements[name]["start"]
                )
        
        def get_duration(self, name):
            return self.measurements.get(name, {}).get("duration", 0)
    
    return PerformanceTracker()


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test"""
    yield
    # Add any cleanup code here


# Custom markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "neural: mark test as neural processing related"
    )
    config.addinivalue_line(
        "markers", "memory: mark test as memory system related"
    )
    config.addinivalue_line(
        "markers", "cache: mark test as caching system related"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security feature related"
    )
    config.addinivalue_line(
        "markers", "mcp: mark test as MCP protocol related"
    )