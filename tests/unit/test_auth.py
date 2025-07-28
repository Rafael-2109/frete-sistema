"""
Unit tests for authentication system
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import jwt
from src.auth.mcp_auth import MCPAuth, AuthError, TokenExpiredError


class TestMCPAuth:
    """Test cases for MCP authentication system"""
    
    @pytest.fixture
    def auth_system(self):
        """Create auth system instance for testing"""
        return MCPAuth(secret_key="test-secret-key-123")
    
    @pytest.fixture
    def valid_token_data(self):
        """Valid token payload"""
        return {
            "user_id": "test-user-123",
            "roles": ["freight_manager", "admin"],
            "permissions": ["freight:read", "freight:write"],
            "session_id": "session-456"
        }
    
    def test_generate_token_success(self, auth_system, valid_token_data):
        """Test successful token generation"""
        token = auth_system.generate_token(
            user_id=valid_token_data["user_id"],
            roles=valid_token_data["roles"],
            permissions=valid_token_data["permissions"],
            session_id=valid_token_data["session_id"]
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token
        decoded = jwt.decode(
            token, 
            auth_system.secret_key, 
            algorithms=[auth_system.algorithm]
        )
        
        assert decoded["user_id"] == valid_token_data["user_id"]
        assert decoded["roles"] == valid_token_data["roles"]
        assert decoded["permissions"] == valid_token_data["permissions"]
        assert "exp" in decoded
        assert "iat" in decoded
    
    def test_generate_token_with_custom_expiry(self, auth_system):
        """Test token generation with custom expiry"""
        token = auth_system.generate_token(
            user_id="test-user",
            roles=["user"],
            expiry_hours=24
        )
        
        decoded = jwt.decode(
            token,
            auth_system.secret_key,
            algorithms=[auth_system.algorithm]
        )
        
        # Check expiry is approximately 24 hours from now
        exp_time = datetime.fromtimestamp(decoded["exp"])
        expected_exp = datetime.utcnow() + timedelta(hours=24)
        
        assert abs((exp_time - expected_exp).total_seconds()) < 60  # Within 1 minute
    
    def test_validate_token_success(self, auth_system, valid_token_data):
        """Test successful token validation"""
        token = auth_system.generate_token(**valid_token_data)
        
        result = auth_system.validate_token(token)
        
        assert result["valid"] is True
        assert result["user_id"] == valid_token_data["user_id"]
        assert result["roles"] == valid_token_data["roles"]
        assert result["permissions"] == valid_token_data["permissions"]
    
    def test_validate_token_expired(self, auth_system):
        """Test validation of expired token"""
        # Generate token that's already expired
        token = auth_system.generate_token(
            user_id="test-user",
            roles=["user"],
            expiry_hours=-1  # Expired 1 hour ago
        )
        
        with pytest.raises(TokenExpiredError):
            auth_system.validate_token(token)
    
    def test_validate_token_invalid_signature(self, auth_system):
        """Test validation with invalid signature"""
        # Generate token with different secret
        wrong_auth = MCPAuth(secret_key="wrong-secret")
        token = wrong_auth.generate_token(
            user_id="test-user",
            roles=["user"]
        )
        
        with pytest.raises(AuthError) as exc_info:
            auth_system.validate_token(token)
        
        assert "Invalid token signature" in str(exc_info.value)
    
    def test_validate_token_malformed(self, auth_system):
        """Test validation of malformed token"""
        malformed_tokens = [
            "not.a.token",
            "invalid-jwt-format",
            "",
            "eyJ0eXAiOiJKV1QiLCJhbGc.invalid.signature"
        ]
        
        for bad_token in malformed_tokens:
            with pytest.raises(AuthError):
                auth_system.validate_token(bad_token)
    
    def test_refresh_token_success(self, auth_system, valid_token_data):
        """Test successful token refresh"""
        original_token = auth_system.generate_token(**valid_token_data)
        
        # Wait a moment to ensure different iat
        import time
        time.sleep(0.1)
        
        new_token = auth_system.refresh_token(original_token)
        
        assert new_token != original_token
        
        # Validate new token has same data
        new_data = auth_system.validate_token(new_token)
        assert new_data["user_id"] == valid_token_data["user_id"]
        assert new_data["roles"] == valid_token_data["roles"]
        assert new_data["permissions"] == valid_token_data["permissions"]
    
    def test_refresh_token_expired(self, auth_system):
        """Test refresh of expired token fails"""
        expired_token = auth_system.generate_token(
            user_id="test-user",
            roles=["user"],
            expiry_hours=-1
        )
        
        with pytest.raises(TokenExpiredError):
            auth_system.refresh_token(expired_token)
    
    def test_revoke_token(self, auth_system, valid_token_data):
        """Test token revocation"""
        token = auth_system.generate_token(**valid_token_data)
        
        # Token should be valid initially
        assert auth_system.validate_token(token)["valid"] is True
        
        # Revoke the token
        auth_system.revoke_token(token)
        
        # Token should now be invalid
        with pytest.raises(AuthError) as exc_info:
            auth_system.validate_token(token)
        
        assert "Token has been revoked" in str(exc_info.value)
    
    def test_check_permission_success(self, auth_system):
        """Test permission checking"""
        token = auth_system.generate_token(
            user_id="test-user",
            roles=["admin"],
            permissions=["freight:read", "freight:write", "users:manage"]
        )
        
        assert auth_system.check_permission(token, "freight:read") is True
        assert auth_system.check_permission(token, "freight:write") is True
        assert auth_system.check_permission(token, "users:manage") is True
    
    def test_check_permission_denied(self, auth_system):
        """Test permission denied"""
        token = auth_system.generate_token(
            user_id="test-user",
            roles=["user"],
            permissions=["freight:read"]
        )
        
        assert auth_system.check_permission(token, "freight:write") is False
        assert auth_system.check_permission(token, "users:manage") is False
    
    def test_check_role_success(self, auth_system):
        """Test role checking"""
        token = auth_system.generate_token(
            user_id="test-user",
            roles=["admin", "freight_manager"]
        )
        
        assert auth_system.check_role(token, "admin") is True
        assert auth_system.check_role(token, "freight_manager") is True
    
    def test_check_role_denied(self, auth_system):
        """Test role denied"""
        token = auth_system.generate_token(
            user_id="test-user",
            roles=["user"]
        )
        
        assert auth_system.check_role(token, "admin") is False
        assert auth_system.check_role(token, "freight_manager") is False
    
    def test_token_cleanup(self, auth_system):
        """Test cleanup of revoked tokens"""
        # Generate and revoke multiple tokens
        tokens = []
        for i in range(5):
            token = auth_system.generate_token(
                user_id=f"user-{i}",
                roles=["user"]
            )
            tokens.append(token)
            auth_system.revoke_token(token)
        
        # Check all are revoked
        for token in tokens:
            with pytest.raises(AuthError):
                auth_system.validate_token(token)
        
        # Cleanup old revoked tokens
        auth_system.cleanup_revoked_tokens(max_age_hours=0)
        
        # Implementation specific: check internal state if accessible
        # This depends on the actual implementation
    
    def test_concurrent_token_operations(self, auth_system):
        """Test thread safety of token operations"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def generate_and_validate():
            try:
                token = auth_system.generate_token(
                    user_id="concurrent-user",
                    roles=["user"]
                )
                validation = auth_system.validate_token(token)
                results.put((token, validation))
            except Exception as e:
                errors.put(e)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=generate_and_validate)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check results
        assert errors.empty(), "No errors should occur in concurrent operations"
        assert results.qsize() == 10, "All operations should complete"
        
        # Verify all tokens are unique and valid
        seen_tokens = set()
        while not results.empty():
            token, validation = results.get()
            assert token not in seen_tokens, "Tokens should be unique"
            seen_tokens.add(token)
            assert validation["valid"] is True


class TestAuthIntegration:
    """Integration tests for auth system with other components"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database for integration tests"""
        return MagicMock()
    
    @pytest.fixture
    def auth_with_db(self, mock_db):
        """Auth system with database integration"""
        auth = MCPAuth(secret_key="test-secret", db=mock_db)
        return auth
    
    def test_auth_with_user_lookup(self, auth_with_db, mock_db):
        """Test auth with user database lookup"""
        # Mock user data
        mock_db.get_user.return_value = {
            "id": "user-123",
            "roles": ["admin"],
            "permissions": ["all"],
            "active": True
        }
        
        # Generate token for user
        token = auth_with_db.generate_token_for_user("user-123")
        
        # Verify database was called
        mock_db.get_user.assert_called_once_with("user-123")
        
        # Validate token
        result = auth_with_db.validate_token(token)
        assert result["user_id"] == "user-123"
        assert result["roles"] == ["admin"]
    
    def test_auth_with_inactive_user(self, auth_with_db, mock_db):
        """Test auth denies inactive users"""
        mock_db.get_user.return_value = {
            "id": "user-123",
            "active": False
        }
        
        with pytest.raises(AuthError) as exc_info:
            auth_with_db.generate_token_for_user("user-123")
        
        assert "User is not active" in str(exc_info.value)
    
    @patch('src.auth.mcp_auth.redis_client')
    def test_auth_with_redis_cache(self, mock_redis, auth_system):
        """Test auth with Redis caching"""
        # Generate token
        token = auth_system.generate_token(
            user_id="cached-user",
            roles=["user"]
        )
        
        # First validation should cache
        auth_system.validate_token(token)
        
        # Second validation should use cache
        auth_system.validate_token(token)
        
        # Verify Redis operations
        assert mock_redis.get.called
        assert mock_redis.setex.called