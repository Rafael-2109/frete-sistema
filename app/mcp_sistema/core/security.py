"""
Security utilities for MCP Sistema
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging
import secrets
import string
from enum import Enum

from .settings import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(Enum):
    """Token types for JWT"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"


class SecurityLevel(Enum):
    """Security levels for operations"""
    PUBLIC = 0
    AUTHENTICATED = 1
    VERIFIED = 2
    ADMIN = 3
    SUPERUSER = 4


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    token_type: TokenType = TokenType.ACCESS
) -> str:
    """
    Create a JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        if token_type == TokenType.ACCESS:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        elif token_type == TokenType.REFRESH:
            expire = datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        elif token_type == TokenType.RESET_PASSWORD:
            expire = datetime.utcnow() + timedelta(hours=1)
        elif token_type == TokenType.EMAIL_VERIFICATION:
            expire = datetime.utcnow() + timedelta(days=7)
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": token_type.value
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token
    """
    return create_access_token(
        data, 
        expires_delta=expires_delta,
        token_type=TokenType.REFRESH
    )


def verify_token(
    token: str, 
    expected_type: Optional[TokenType] = None,
    verify_exp: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": verify_exp}
        )
        
        # Verify token type if specified
        if expected_type and payload.get("type") != expected_type.value:
            logger.error(f"Invalid token type: expected {expected_type.value}, got {payload.get('type')}")
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        return None
    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        return None


def create_api_key(prefix: str = "mcp", length: int = 32) -> str:
    """
    Generate a secure API key with prefix
    """
    key = secrets.token_urlsafe(length)
    return f"{prefix}_{key}"


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a secure random password
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def create_token_pair(user_data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Create both access and refresh tokens
    """
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(user_data)
    return access_token, refresh_token


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage
    """
    # Use a simpler hash for API keys (they're already secure random strings)
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash
    """
    return hash_api_key(plain_key) == hashed_key


class SecurityContext:
    """
    Security context for request handling
    """
    def __init__(self, user: Optional[Dict[str, Any]] = None):
        self.user = user
        self.is_authenticated = user is not None
        self.is_verified = user and user.get("is_verified", False)
        self.is_admin = user and ("admin" in user.get("roles", []) or user.get("is_superuser", False))
        self.is_superuser = user and user.get("is_superuser", False)
        self.user_id = user.get("sub") if user else None
        self.username = user.get("username") if user else None
        self.email = user.get("email") if user else None
        self.roles = user.get("roles", []) if user else []
        self.permissions = user.get("permissions", []) if user else []
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has specific permission
        """
        if not self.is_authenticated:
            return False
        
        if self.is_superuser:
            return True
        
        return permission in self.permissions
    
    def has_any_permission(self, *permissions: str) -> bool:
        """
        Check if user has any of the specified permissions
        """
        return any(self.has_permission(perm) for perm in permissions)
    
    def has_all_permissions(self, *permissions: str) -> bool:
        """
        Check if user has all of the specified permissions
        """
        return all(self.has_permission(perm) for perm in permissions)
    
    def has_role(self, role: str) -> bool:
        """
        Check if user has specific role
        """
        if not self.is_authenticated:
            return False
        
        return role in self.roles
    
    def has_any_role(self, *roles: str) -> bool:
        """
        Check if user has any of the specified roles
        """
        return any(self.has_role(role) for role in roles)
    
    def require_permission(self, permission: str) -> None:
        """
        Require specific permission, raise exception if not granted
        """
        if not self.has_permission(permission):
            raise PermissionError(f"Permission '{permission}' required")
    
    def require_any_permission(self, *permissions: str) -> None:
        """
        Require any of the specified permissions
        """
        if not self.has_any_permission(*permissions):
            raise PermissionError(f"One of these permissions required: {', '.join(permissions)}")
    
    def require_all_permissions(self, *permissions: str) -> None:
        """
        Require all of the specified permissions
        """
        if not self.has_all_permissions(*permissions):
            raise PermissionError(f"All of these permissions required: {', '.join(permissions)}")
    
    def require_role(self, role: str) -> None:
        """
        Require specific role
        """
        if not self.has_role(role):
            raise PermissionError(f"Role '{role}' required")
    
    def require_authenticated(self) -> None:
        """
        Require user to be authenticated
        """
        if not self.is_authenticated:
            raise PermissionError("Authentication required")
    
    def require_verified(self) -> None:
        """
        Require user to be verified
        """
        if not self.is_verified:
            raise PermissionError("Email verification required")
    
    def require_admin(self) -> None:
        """
        Require user to be admin
        """
        if not self.is_admin:
            raise PermissionError("Admin privileges required")
    
    def require_superuser(self) -> None:
        """
        Require user to be superuser
        """
        if not self.is_superuser:
            raise PermissionError("Superuser privileges required")
    
    def get_security_level(self) -> SecurityLevel:
        """
        Get the current user's security level
        """
        if self.is_superuser:
            return SecurityLevel.SUPERUSER
        elif self.is_admin:
            return SecurityLevel.ADMIN
        elif self.is_verified:
            return SecurityLevel.VERIFIED
        elif self.is_authenticated:
            return SecurityLevel.AUTHENTICATED
        else:
            return SecurityLevel.PUBLIC
    
    def check_security_level(self, required_level: SecurityLevel) -> bool:
        """
        Check if user meets the required security level
        """
        return self.get_security_level().value >= required_level.value
    
    def require_security_level(self, required_level: SecurityLevel) -> None:
        """
        Require a minimum security level
        """
        if not self.check_security_level(required_level):
            raise PermissionError(f"Security level {required_level.name} required")


# Password validation functions
def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if not any(c in string.punctuation for c in password):
        return False, "Password must contain at least one special character"
    
    return True, None


# Rate limiting helpers
def generate_rate_limit_key(identifier: str, operation: str) -> str:
    """
    Generate a key for rate limiting
    """
    return f"rate_limit:{operation}:{identifier}"


def check_rate_limit(
    identifier: str,
    operation: str,
    max_attempts: int,
    window_seconds: int,
    current_attempts: int
) -> Tuple[bool, int]:
    """
    Check if rate limit has been exceeded
    Returns (is_allowed, remaining_attempts)
    """
    remaining = max_attempts - current_attempts
    is_allowed = remaining > 0
    return is_allowed, max(0, remaining)