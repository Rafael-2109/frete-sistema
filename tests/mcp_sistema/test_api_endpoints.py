"""
Tests for MCP API endpoints
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from fastapi.testclient import TestClient
from app.mcp_sistema.models.user import User
from app.mcp_sistema.models.mcp_models import QueryLog, UserPreference


class TestAuthEndpoints:
    """Test suite for authentication endpoints"""
    
    def test_register_user(self, client: TestClient):
        """Test user registration endpoint"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "user" in data["data"]
        assert data["data"]["user"]["username"] == "testuser"
    
    def test_register_duplicate_user(self, client: TestClient, test_user):
        """Test registration with existing username"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user.username,
                "email": "another@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "USER_EXISTS"
    
    def test_login_success(self, client: TestClient, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_user",
                "password": "test_password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_user",
                "password": "wrong_password"
            }
        )
        
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    
    def test_refresh_token(self, client: TestClient, test_user, jwt_service):
        """Test token refresh"""
        # Get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_user",
                "password": "test_password123"
            }
        )
        
        refresh_token = login_response.json()["data"]["refresh_token"]
        
        # Refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()["data"]
    
    def test_logout(self, client: TestClient, auth_headers):
        """Test logout endpoint"""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["data"]["message"] == "Logged out successfully"
    
    def test_protected_endpoint_without_auth(self, client: TestClient):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401
    
    def test_protected_endpoint_with_auth(self, client: TestClient, auth_headers):
        """Test accessing protected endpoint with authentication"""
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200


class TestMCPEndpoints:
    """Test suite for MCP-specific endpoints"""
    
    def test_process_query(self, client: TestClient, auth_headers):
        """Test query processing endpoint"""
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "criar embarque para São Paulo",
                "context": {}
            }
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert "intent" in data
        assert "entities" in data
        assert "confidence" in data
        assert data["intent"] == "create_shipment"
    
    def test_process_query_with_context(self, client: TestClient, auth_headers):
        """Test query processing with context"""
        # First query
        response1 = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "verificar frete 12345"
            }
        )
        
        # Second query with context
        response2 = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                "query": "qual o valor",
                "use_context": True
            }
        )
        
        assert response2.status_code == 200
        data = response2.json()["data"]
        assert "freight_id" in data["entities"]
    
    def test_query_suggestions(self, client: TestClient, auth_headers):
        """Test query suggestions endpoint"""
        response = client.get(
            "/api/v1/mcp/suggestions?partial=criar emb",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        suggestions = response.json()["data"]["suggestions"]
        assert len(suggestions) > 0
        assert any("embarque" in s for s in suggestions)
    
    def test_query_history(self, client: TestClient, auth_headers, db_session):
        """Test query history endpoint"""
        # Create some queries
        queries = ["criar embarque", "verificar status", "aprovar frete"]
        for query in queries:
            client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
        
        # Get history
        response = client.get(
            "/api/v1/mcp/history?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        history = response.json()["data"]["queries"]
        assert len(history) >= 3
        assert history[0]["query"] == "aprovar frete"  # Most recent first
    
    def test_entity_feedback(self, client: TestClient, auth_headers):
        """Test entity mapping feedback endpoint"""
        response = client.post(
            "/api/v1/mcp/feedback/entity",
            headers=auth_headers,
            json={
                "entity_type": "action",
                "entity_value": "liberar",
                "correct_value": "release",
                "query_id": "test-query-123"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["data"]["message"] == "Feedback recorded successfully"
    
    def test_intent_feedback(self, client: TestClient, auth_headers):
        """Test intent correction feedback"""
        response = client.post(
            "/api/v1/mcp/feedback/intent",
            headers=auth_headers,
            json={
                "query_id": "test-query-123",
                "original_intent": "check_status",
                "correct_intent": "track_shipment"
            }
        )
        
        assert response.status_code == 200
    
    def test_batch_query_processing(self, client: TestClient, auth_headers):
        """Test batch query processing"""
        response = client.post(
            "/api/v1/mcp/batch",
            headers=auth_headers,
            json={
                "queries": [
                    "criar embarque",
                    "verificar status",
                    "aprovar frete pendente"
                ]
            }
        )
        
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 3
        assert all("intent" in r for r in results)


class TestUserPreferenceEndpoints:
    """Test suite for user preference endpoints"""
    
    def test_get_preferences(self, client: TestClient, auth_headers, user_preferences):
        """Test getting user preferences"""
        response = client.get(
            "/api/v1/users/preferences",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        prefs = response.json()["data"]["preferences"]
        assert prefs["language"] == "pt-BR"
        assert prefs["default_view"] == "dashboard"
    
    def test_update_preferences(self, client: TestClient, auth_headers):
        """Test updating user preferences"""
        response = client.put(
            "/api/v1/users/preferences",
            headers=auth_headers,
            json={
                "language": "en-US",
                "notifications": "disabled",
                "theme": "dark"
            }
        )
        
        assert response.status_code == 200
        updated = response.json()["data"]["preferences"]
        assert updated["language"] == "en-US"
        assert updated["theme"] == "dark"
    
    def test_delete_preference(self, client: TestClient, auth_headers, user_preferences):
        """Test deleting a specific preference"""
        response = client.delete(
            "/api/v1/users/preferences/notifications",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify deleted
        get_response = client.get(
            "/api/v1/users/preferences",
            headers=auth_headers
        )
        prefs = get_response.json()["data"]["preferences"]
        assert "notifications" not in prefs


class TestHealthEndpoints:
    """Test suite for health check endpoints"""
    
    def test_basic_health(self, client: TestClient):
        """Test basic health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_detailed_health(self, client: TestClient):
        """Test detailed health endpoint"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        health = response.json()["data"]
        assert health["status"] == "healthy"
        assert "database" in health["checks"]
        assert "cache" in health["checks"]
        assert "nlp" in health["checks"]
    
    def test_readiness_check(self, client: TestClient):
        """Test readiness endpoint"""
        response = client.get("/api/v1/health/ready")
        
        assert response.status_code == 200
        assert response.json()["data"]["ready"] is True
    
    def test_liveness_check(self, client: TestClient):
        """Test liveness endpoint"""
        response = client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        assert response.json()["data"]["alive"] is True


class TestRateLimiting:
    """Test suite for rate limiting"""
    
    def test_rate_limit_enforcement(self, client: TestClient, auth_headers):
        """Test rate limit is enforced"""
        # Make many requests quickly
        responses = []
        for i in range(150):  # Exceed default limit of 100/min
            response = client.get(
                "/api/v1/mcp/suggestions?partial=test",
                headers=auth_headers
            )
            responses.append(response)
            
            if response.status_code == 429:
                break
        
        # Should hit rate limit
        assert any(r.status_code == 429 for r in responses)
        
        # Check rate limit headers
        limited_response = next(r for r in responses if r.status_code == 429)
        assert "X-RateLimit-Limit" in limited_response.headers
        assert "X-RateLimit-Remaining" in limited_response.headers
        assert "X-RateLimit-Reset" in limited_response.headers
    
    def test_rate_limit_per_user(self, client: TestClient, auth_headers, jwt_service):
        """Test rate limiting is per-user"""
        # Create second user token
        token2 = jwt_service.create_access_token({"sub": "user2", "user_id": 2})
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # Exhaust rate limit for user 1
        for i in range(105):
            client.get("/api/v1/mcp/suggestions?partial=test", headers=auth_headers)
        
        # User 2 should still be able to make requests
        response = client.get(
            "/api/v1/mcp/suggestions?partial=test",
            headers=headers2
        )
        assert response.status_code == 200


class TestErrorHandling:
    """Test suite for API error handling"""
    
    def test_validation_error(self, client: TestClient, auth_headers):
        """Test validation error response"""
        response = client.post(
            "/api/v1/mcp/query",
            headers=auth_headers,
            json={
                # Missing required 'query' field
                "context": {}
            }
        )
        
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "details" in error
    
    def test_not_found_error(self, client: TestClient, auth_headers):
        """Test 404 error response"""
        response = client.get(
            "/api/v1/nonexistent/endpoint",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
    
    def test_internal_server_error(self, client: TestClient, auth_headers):
        """Test 500 error handling"""
        with patch('app.mcp_sistema.api.v1.mcp.process_query') as mock:
            mock.side_effect = Exception("Unexpected error")
            
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": "test query"}
            )
            
            assert response.status_code == 500
            error = response.json()["error"]
            assert error["code"] == "INTERNAL_ERROR"
            assert "request_id" in error  # Should include request ID for tracking


class TestCORS:
    """Test suite for CORS configuration"""
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present"""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
    
    def test_cors_allowed_origin(self, client: TestClient):
        """Test request from allowed origin"""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"