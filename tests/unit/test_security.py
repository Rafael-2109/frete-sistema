"""
Unit tests for security features
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
import hashlib
import secrets
import json
from src.security.security_manager import (
    SecurityManager,
    RateLimiter,
    InputValidator,
    EncryptionManager,
    SecurityError,
    RateLimitExceeded,
    ValidationError
)


class TestRateLimiter:
    """Test cases for rate limiting functionality"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance"""
        return RateLimiter(
            max_requests=10,
            window_seconds=60,
            backend="memory"
        )
    
    @pytest.fixture
    def redis_rate_limiter(self, mock_redis):
        """Create rate limiter with Redis backend"""
        limiter = RateLimiter(
            max_requests=5,
            window_seconds=60,
            backend="redis"
        )
        limiter.redis_client = mock_redis
        return limiter
    
    def test_allow_request_within_limit(self, rate_limiter):
        """Test allowing requests within rate limit"""
        identifier = "user-123"
        
        # Should allow first requests
        for i in range(5):
            assert rate_limiter.check_rate_limit(identifier) is True
    
    def test_block_request_exceeding_limit(self, rate_limiter):
        """Test blocking requests exceeding rate limit"""
        identifier = "user-123"
        rate_limiter.max_requests = 3
        
        # Use up the limit
        for i in range(3):
            rate_limiter.check_rate_limit(identifier)
        
        # Next request should be blocked
        with pytest.raises(RateLimitExceeded) as exc_info:
            rate_limiter.check_rate_limit(identifier)
        
        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retry_after > 0
    
    def test_sliding_window(self, rate_limiter):
        """Test sliding window rate limiting"""
        identifier = "user-123"
        rate_limiter.max_requests = 2
        rate_limiter.window_seconds = 2
        
        # Two requests at t=0
        assert rate_limiter.check_rate_limit(identifier) is True
        assert rate_limiter.check_rate_limit(identifier) is True
        
        # Should be blocked immediately
        with pytest.raises(RateLimitExceeded):
            rate_limiter.check_rate_limit(identifier)
        
        # Wait for window to slide
        import time
        time.sleep(2.1)
        
        # Should allow again
        assert rate_limiter.check_rate_limit(identifier) is True
    
    def test_different_identifiers(self, rate_limiter):
        """Test rate limiting per identifier"""
        rate_limiter.max_requests = 2
        
        # Each identifier has its own limit
        assert rate_limiter.check_rate_limit("user-123") is True
        assert rate_limiter.check_rate_limit("user-123") is True
        assert rate_limiter.check_rate_limit("user-456") is True
        assert rate_limiter.check_rate_limit("user-456") is True
        
        # Each should be blocked after limit
        with pytest.raises(RateLimitExceeded):
            rate_limiter.check_rate_limit("user-123")
        
        with pytest.raises(RateLimitExceeded):
            rate_limiter.check_rate_limit("user-456")
    
    def test_redis_rate_limiting(self, redis_rate_limiter, mock_redis):
        """Test rate limiting with Redis backend"""
        identifier = "user-123"
        key = f"rate_limit:{identifier}"
        
        # Mock Redis responses
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        
        # First request
        assert redis_rate_limiter.check_rate_limit(identifier) is True
        
        mock_redis.incr.assert_called_with(key)
        mock_redis.expire.assert_called_with(key, 60)
        
        # Simulate hitting limit
        mock_redis.incr.return_value = 6  # Over limit of 5
        mock_redis.ttl.return_value = 30  # 30 seconds remaining
        
        with pytest.raises(RateLimitExceeded) as exc_info:
            redis_rate_limiter.check_rate_limit(identifier)
        
        assert exc_info.value.retry_after == 30
    
    def test_rate_limit_reset(self, rate_limiter):
        """Test manual rate limit reset"""
        identifier = "user-123"
        rate_limiter.max_requests = 1
        
        # Hit limit
        rate_limiter.check_rate_limit(identifier)
        
        # Should be blocked
        with pytest.raises(RateLimitExceeded):
            rate_limiter.check_rate_limit(identifier)
        
        # Reset limit
        rate_limiter.reset_limit(identifier)
        
        # Should allow again
        assert rate_limiter.check_rate_limit(identifier) is True
    
    def test_custom_rate_limits(self, rate_limiter):
        """Test custom rate limits for different operations"""
        # Configure different limits
        rate_limiter.set_custom_limit(
            "api:freight_calculation",
            max_requests=100,
            window_seconds=3600
        )
        rate_limiter.set_custom_limit(
            "api:user_registration", 
            max_requests=5,
            window_seconds=3600
        )
        
        # Check different operations
        for i in range(5):
            assert rate_limiter.check_rate_limit(
                "user-123",
                operation="api:user_registration"
            ) is True
        
        # Registration should be blocked
        with pytest.raises(RateLimitExceeded):
            rate_limiter.check_rate_limit(
                "user-123",
                operation="api:user_registration"
            )
        
        # But freight calculation should still work
        assert rate_limiter.check_rate_limit(
            "user-123",
            operation="api:freight_calculation"
        ) is True
    
    def test_distributed_rate_limiting(self, redis_rate_limiter, mock_redis):
        """Test distributed rate limiting across multiple instances"""
        identifier = "user-123"
        
        # Simulate multiple instances incrementing
        mock_redis.incr.side_effect = [1, 3, 5, 7]  # Simulating other instances
        
        # Check from our instance
        for i in range(2):
            redis_rate_limiter.check_rate_limit(identifier)
        
        # Should respect global limit
        mock_redis.incr.return_value = 6  # Over limit
        
        with pytest.raises(RateLimitExceeded):
            redis_rate_limiter.check_rate_limit(identifier)


class TestInputValidator:
    """Test cases for input validation"""
    
    @pytest.fixture
    def input_validator(self):
        """Create input validator instance"""
        return InputValidator(
            max_length=1000,
            allowed_patterns={
                "email": r'^[\w\.-]+@[\w\.-]+\.\w+$',
                "phone": r'^\+?1?\d{9,15}$',
                "cep": r'^\d{5}-?\d{3}$'
            }
        )
    
    @pytest.fixture
    def validation_schemas(self):
        """Validation schemas for different inputs"""
        return {
            "freight_request": {
                "origin": {"type": "string", "required": True, "max_length": 100},
                "destination": {"type": "string", "required": True, "max_length": 100},
                "weight": {"type": "number", "required": True, "min": 0.1, "max": 100000},
                "service": {"type": "string", "enum": ["express", "standard", "economy"]}
            },
            "user_registration": {
                "email": {"type": "string", "required": True, "pattern": "email"},
                "password": {"type": "string", "required": True, "min_length": 8},
                "phone": {"type": "string", "pattern": "phone"}
            }
        }
    
    def test_validate_string_input(self, input_validator):
        """Test string input validation"""
        # Valid strings
        assert input_validator.validate_string("Hello World") is True
        assert input_validator.validate_string("São Paulo") is True
        
        # Invalid strings
        with pytest.raises(ValidationError):
            input_validator.validate_string("x" * 1001)  # Too long
        
        with pytest.raises(ValidationError):
            input_validator.validate_string("")  # Empty
        
        with pytest.raises(ValidationError):
            input_validator.validate_string(None)  # None
    
    def test_sanitize_input(self, input_validator):
        """Test input sanitization"""
        dangerous_inputs = [
            ("<script>alert('XSS')</script>", "&lt;script&gt;alert('XSS')&lt;/script&gt;"),
            ("'; DROP TABLE users; --", "'; DROP TABLE users; --"),
            ("<img src=x onerror=alert('XSS')>", "&lt;img src=x onerror=alert('XSS')&gt;"),
            ("Hello\x00World", "HelloWorld"),  # Null bytes
            ("Normal text", "Normal text")
        ]
        
        for dangerous, expected in dangerous_inputs:
            sanitized = input_validator.sanitize(dangerous)
            assert sanitized == expected
    
    def test_validate_with_pattern(self, input_validator):
        """Test pattern-based validation"""
        # Email validation
        assert input_validator.validate_pattern("test@example.com", "email") is True
        assert input_validator.validate_pattern("invalid.email", "email") is False
        
        # Phone validation
        assert input_validator.validate_pattern("+5511999999999", "phone") is True
        assert input_validator.validate_pattern("invalid", "phone") is False
        
        # CEP validation
        assert input_validator.validate_pattern("01310-100", "cep") is True
        assert input_validator.validate_pattern("01310100", "cep") is True
        assert input_validator.validate_pattern("invalid", "cep") is False
    
    def test_validate_schema(self, input_validator, validation_schemas):
        """Test schema-based validation"""
        # Valid freight request
        valid_freight = {
            "origin": "São Paulo",
            "destination": "Rio de Janeiro",
            "weight": 1000,
            "service": "express"
        }
        
        result = input_validator.validate_schema(
            valid_freight,
            validation_schemas["freight_request"]
        )
        assert result["valid"] is True
        
        # Invalid freight request - missing required
        invalid_freight = {
            "origin": "São Paulo",
            "weight": 1000
        }
        
        result = input_validator.validate_schema(
            invalid_freight,
            validation_schemas["freight_request"]
        )
        assert result["valid"] is False
        assert "destination" in result["errors"]
    
    def test_validate_number_ranges(self, input_validator):
        """Test number range validation"""
        schema = {
            "weight": {"type": "number", "min": 0.1, "max": 100000},
            "price": {"type": "number", "min": 0, "decimal_places": 2}
        }
        
        # Valid numbers
        assert input_validator.validate_field(1000, schema["weight"])["valid"]
        assert input_validator.validate_field(99.99, schema["price"])["valid"]
        
        # Invalid numbers
        assert not input_validator.validate_field(0, schema["weight"])["valid"]
        assert not input_validator.validate_field(100001, schema["weight"])["valid"]
        assert not input_validator.validate_field(-10, schema["price"])["valid"]
    
    def test_sql_injection_prevention(self, input_validator):
        """Test SQL injection prevention"""
        sql_injection_attempts = [
            "1' OR '1'='1",
            "'; DROP TABLE users; --",
            "1'; INSERT INTO admin VALUES ('hacker'); --",
            "UNION SELECT * FROM passwords",
            "1' AND SLEEP(5) --"
        ]
        
        for attempt in sql_injection_attempts:
            assert input_validator.is_sql_injection(attempt) is True
            
            # Should raise error when validating
            with pytest.raises(ValidationError) as exc_info:
                input_validator.validate_sql_safe(attempt)
            
            assert "SQL injection" in str(exc_info.value)
    
    def test_path_traversal_prevention(self, input_validator):
        """Test path traversal prevention"""
        path_traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
            "....//....//etc/passwd"
        ]
        
        for attempt in path_traversal_attempts:
            assert input_validator.is_path_traversal(attempt) is True
            
            with pytest.raises(ValidationError) as exc_info:
                input_validator.validate_path_safe(attempt)
            
            assert "Path traversal" in str(exc_info.value)
    
    def test_file_upload_validation(self, input_validator):
        """Test file upload validation"""
        # Configure allowed file types
        input_validator.allowed_file_types = [".jpg", ".png", ".pdf"]
        input_validator.max_file_size = 5 * 1024 * 1024  # 5MB
        
        # Valid files
        valid_files = [
            {"name": "document.pdf", "size": 1024 * 1024},
            {"name": "image.jpg", "size": 2 * 1024 * 1024}
        ]
        
        for file in valid_files:
            assert input_validator.validate_file_upload(file)["valid"]
        
        # Invalid files
        invalid_files = [
            {"name": "script.exe", "size": 1024},  # Forbidden type
            {"name": "large.jpg", "size": 10 * 1024 * 1024},  # Too large
            {"name": "../etc/passwd", "size": 1024}  # Path traversal
        ]
        
        for file in invalid_files:
            assert not input_validator.validate_file_upload(file)["valid"]


class TestEncryptionManager:
    """Test cases for encryption functionality"""
    
    @pytest.fixture
    def encryption_manager(self):
        """Create encryption manager instance"""
        return EncryptionManager(
            key=secrets.token_bytes(32),
            algorithm="AES-256-GCM"
        )
    
    @pytest.fixture
    def sensitive_data(self):
        """Sample sensitive data"""
        return {
            "credit_card": "4111111111111111",
            "cpf": "123.456.789-00",
            "api_key": "sk_test_abcdef123456",
            "password": "super_secret_password"
        }
    
    def test_encrypt_decrypt_string(self, encryption_manager):
        """Test basic encryption and decryption"""
        plaintext = "This is sensitive data"
        
        # Encrypt
        encrypted = encryption_manager.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = encryption_manager.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_json(self, encryption_manager, sensitive_data):
        """Test JSON data encryption"""
        # Encrypt JSON
        encrypted = encryption_manager.encrypt_json(sensitive_data)
        assert isinstance(encrypted, str)
        
        # Decrypt JSON
        decrypted = encryption_manager.decrypt_json(encrypted)
        assert decrypted == sensitive_data
    
    def test_field_level_encryption(self, encryption_manager):
        """Test selective field encryption"""
        data = {
            "user_id": "123",
            "name": "John Doe",
            "cpf": "123.456.789-00",
            "email": "john@example.com",
            "credit_card": "4111111111111111"
        }
        
        # Encrypt specific fields
        encrypted_data = encryption_manager.encrypt_fields(
            data,
            fields=["cpf", "credit_card"]
        )
        
        # Non-sensitive fields remain plain
        assert encrypted_data["user_id"] == "123"
        assert encrypted_data["name"] == "John Doe"
        
        # Sensitive fields are encrypted
        assert encrypted_data["cpf"] != data["cpf"]
        assert encrypted_data["credit_card"] != data["credit_card"]
        
        # Decrypt fields
        decrypted_data = encryption_manager.decrypt_fields(
            encrypted_data,
            fields=["cpf", "credit_card"]
        )
        
        assert decrypted_data == data
    
    def test_encryption_with_wrong_key(self, encryption_manager):
        """Test decryption with wrong key fails"""
        plaintext = "Secret data"
        encrypted = encryption_manager.encrypt(plaintext)
        
        # Create manager with different key
        wrong_manager = EncryptionManager(
            key=secrets.token_bytes(32),
            algorithm="AES-256-GCM"
        )
        
        # Should fail to decrypt
        with pytest.raises(SecurityError):
            wrong_manager.decrypt(encrypted)
    
    def test_key_derivation(self, encryption_manager):
        """Test key derivation from password"""
        password = "user_password_123"
        salt = b"static_salt_for_test"
        
        # Derive key
        key1 = encryption_manager.derive_key(password, salt)
        key2 = encryption_manager.derive_key(password, salt)
        
        # Same password and salt should produce same key
        assert key1 == key2
        
        # Different password should produce different key
        key3 = encryption_manager.derive_key("different_password", salt)
        assert key1 != key3
    
    def test_hash_password(self, encryption_manager):
        """Test password hashing"""
        password = "user_password_123"
        
        # Hash password
        hashed = encryption_manager.hash_password(password)
        
        # Verify correct password
        assert encryption_manager.verify_password(password, hashed) is True
        
        # Verify wrong password
        assert encryption_manager.verify_password("wrong_password", hashed) is False
    
    def test_generate_secure_token(self, encryption_manager):
        """Test secure token generation"""
        # Generate tokens
        token1 = encryption_manager.generate_token(32)
        token2 = encryption_manager.generate_token(32)
        
        # Should be unique
        assert token1 != token2
        
        # Should have correct length
        assert len(token1) == 64  # 32 bytes = 64 hex chars
    
    def test_data_masking(self, encryption_manager):
        """Test data masking for logs"""
        sensitive_data = {
            "credit_card": "4111111111111111",
            "cpf": "123.456.789-00",
            "email": "user@example.com",
            "phone": "+5511999999999"
        }
        
        masked = encryption_manager.mask_sensitive_data(sensitive_data)
        
        assert masked["credit_card"] == "411111******1111"
        assert masked["cpf"] == "123.***.***-**"
        assert masked["email"] == "u***@example.com"
        assert masked["phone"] == "+551199****999"


class TestSecurityManager:
    """Test cases for integrated security management"""
    
    @pytest.fixture
    def security_manager(self):
        """Create security manager instance"""
        return SecurityManager(
            rate_limiter_enabled=True,
            encryption_enabled=True,
            validation_enabled=True
        )
    
    @pytest.fixture
    def api_request(self):
        """Sample API request"""
        return {
            "user_id": "user-123",
            "ip_address": "192.168.1.1",
            "endpoint": "/api/freight/calculate",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer token123",
                "User-Agent": "Mozilla/5.0"
            },
            "body": {
                "origin": "São Paulo",
                "destination": "Rio de Janeiro",
                "weight": 1000
            }
        }
    
    def test_request_validation_pipeline(self, security_manager, api_request):
        """Test complete request validation pipeline"""
        # Process request through security pipeline
        result = security_manager.validate_request(api_request)
        
        assert result["valid"] is True
        assert "rate_limit_remaining" in result
        assert result["sanitized_body"] is not None
    
    def test_security_headers(self, security_manager):
        """Test security headers generation"""
        headers = security_manager.get_security_headers()
        
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
    
    def test_audit_logging(self, security_manager, api_request):
        """Test security audit logging"""
        with patch.object(security_manager, 'log_audit') as mock_log:
            # Simulate security event
            security_manager.log_security_event(
                event_type="rate_limit_exceeded",
                user_id=api_request["user_id"],
                ip_address=api_request["ip_address"],
                details={"endpoint": api_request["endpoint"]}
            )
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            
            assert call_args["event_type"] == "rate_limit_exceeded"
            assert call_args["user_id"] == "user-123"
            assert call_args["ip_address"] == "192.168.1.1"
    
    def test_ip_blacklisting(self, security_manager):
        """Test IP blacklisting functionality"""
        malicious_ip = "10.0.0.1"
        
        # Add to blacklist
        security_manager.blacklist_ip(malicious_ip, reason="Repeated attacks")
        
        # Check if blocked
        assert security_manager.is_ip_blocked(malicious_ip) is True
        
        # Remove from blacklist
        security_manager.unblock_ip(malicious_ip)
        assert security_manager.is_ip_blocked(malicious_ip) is False
    
    def test_anomaly_detection(self, security_manager):
        """Test anomaly detection in requests"""
        # Normal request pattern
        normal_requests = [
            {"endpoint": "/api/freight", "response_time": 100},
            {"endpoint": "/api/freight", "response_time": 120},
            {"endpoint": "/api/freight", "response_time": 110}
        ]
        
        for req in normal_requests:
            security_manager.record_request_metric(req)
        
        # Anomalous request
        anomaly = {"endpoint": "/api/freight", "response_time": 5000}
        
        is_anomaly = security_manager.detect_anomaly(anomaly)
        assert is_anomaly is True
    
    def test_session_security(self, security_manager):
        """Test session security features"""
        user_id = "user-123"
        
        # Create secure session
        session = security_manager.create_session(
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        assert session["token"] is not None
        assert session["expires_at"] > datetime.utcnow()
        
        # Validate session
        is_valid = security_manager.validate_session(
            token=session["token"],
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        assert is_valid is True
        
        # Invalid session (different IP)
        is_valid = security_manager.validate_session(
            token=session["token"],
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0"
        )
        assert is_valid is False