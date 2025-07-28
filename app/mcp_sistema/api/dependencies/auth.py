"""
Authentication dependencies
"""
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, Union
import logging

from ...core.security import (
    verify_token, 
    verify_api_key,
    SecurityContext,
    TokenType,
    SecurityLevel
)
from ...models.database import get_db
from ...models.user import User, APIKey

logger = logging.getLogger(__name__)

# Security schemes
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Extract and verify JWT token payload
    """
    token = credentials.credentials
    
    payload = verify_token(token, expected_type=TokenType.ACCESS)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    if current_user.is_locked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked"
        )
    
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return current_user


async def get_api_key_from_header(
    x_api_key: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract API key from header
    """
    return x_api_key


async def get_user_from_api_key(
    api_key: Optional[str] = Depends(get_api_key_from_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get user from API key
    """
    if not api_key:
        return None
    
    # Find API key in database
    api_key_obj = None
    all_keys = db.query(APIKey).filter(APIKey.is_active == True).all()
    
    for key in all_keys:
        if verify_api_key(api_key, key.key):
            api_key_obj = key
            break
    
    if not api_key_obj or not api_key_obj.is_valid():
        return None
    
    # Update last used
    api_key_obj.update_last_used()
    db.commit()
    
    return api_key_obj.user


async def get_current_user_flexible(
    token_user: Optional[User] = Depends(get_current_user),
    api_key_user: Optional[User] = Depends(get_user_from_api_key)
) -> User:
    """
    Get current user from either JWT token or API key
    """
    # Prefer token authentication
    if token_user:
        return token_user
    
    if api_key_user:
        return api_key_user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No valid authentication provided"
    )


def get_security_context(
    user: Optional[User] = None
) -> SecurityContext:
    """
    Create security context from user
    """
    if user:
        return SecurityContext(user.to_token_payload())
    return SecurityContext()


# Permission decorators as dependencies
def require_permission(permission: str):
    """
    Dependency to require specific permission
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        context = get_security_context(current_user)
        context.require_permission(permission)
        return current_user
    
    return permission_checker


def require_any_permission(*permissions: str):
    """
    Dependency to require any of the specified permissions
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        context = get_security_context(current_user)
        context.require_any_permission(*permissions)
        return current_user
    
    return permission_checker


def require_all_permissions(*permissions: str):
    """
    Dependency to require all of the specified permissions
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        context = get_security_context(current_user)
        context.require_all_permissions(*permissions)
        return current_user
    
    return permission_checker


def require_role(role: str):
    """
    Dependency to require specific role
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        context = get_security_context(current_user)
        context.require_role(role)
        return current_user
    
    return role_checker


def require_admin():
    """
    Dependency to require admin role
    """
    async def admin_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        context = get_security_context(current_user)
        context.require_admin()
        return current_user
    
    return admin_checker


def require_superuser():
    """
    Dependency to require superuser privileges
    """
    async def superuser_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        context = get_security_context(current_user)
        context.require_superuser()
        return current_user
    
    return superuser_checker


def require_security_level(level: SecurityLevel):
    """
    Dependency to require minimum security level
    """
    async def security_level_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        context = get_security_context(current_user)
        context.require_security_level(level)
        return current_user
    
    return security_level_checker


# Rate limiting dependencies
async def check_login_rate_limit(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Check rate limit for login attempts
    """
    # TODO: Implement rate limiting with Redis or in-memory cache
    # For now, just pass through
    pass


# MCP-specific authentication
async def get_mcp_client(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get MCP client user
    """
    if not current_user.mcp_client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MCP client access required"
        )
    
    return current_user


# Optional authentication (for endpoints that work with or without auth)
async def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None
    """
    try:
        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_token(token, expected_type=TokenType.ACCESS)
            if payload:
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == int(user_id)).first()
                    if user and user.is_active:
                        return user
        
        # Try to get API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            user = await get_user_from_api_key(api_key, db)
            if user and user.is_active:
                return user
        
    except Exception:
        pass
    
    return None