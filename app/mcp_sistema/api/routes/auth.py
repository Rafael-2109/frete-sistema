"""
Authentication routes for MCP Sistema
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, EmailStr, Field, validator
import logging

from ...core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    verify_token,
    TokenType,
    SecurityContext,
    validate_password_strength,
    create_api_key,
    generate_secure_password,
    hash_api_key
)
from ...core.settings import settings
from ...models.database import get_db
from ...models.user import User, RefreshToken, APIKey, Role, Permission
from ..dependencies.auth import get_current_user, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# Pydantic models for requests/responses
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    is_superuser: bool
    roles: list[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)
    permissions: Optional[list[str]] = []


class APIKeyResponse(BaseModel):
    id: int
    key: str  # Only returned on creation
    name: str
    description: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime


class PasswordReset(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class EmailVerification(BaseModel):
    token: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        or_(
            User.username == user_data.username,
            User.email == user_data.email
        )
    ).first()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create new user
    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name
    )
    user.set_password(user_data.password)
    
    # Assign default role if it exists
    default_role = db.query(Role).filter(Role.name == "user").first()
    if default_role:
        user.roles.append(default_role)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"New user registered: {user.username}")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        created_at=user.created_at
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with username and password
    """
    # Find user by username or email
    user = db.query(User).filter(
        or_(
            User.username == form_data.username,
            User.email == form_data.username
        )
    ).first()
    
    if not user:
        logger.warning(f"Login attempt for non-existent user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if user.is_locked():
        logger.warning(f"Login attempt for locked account: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked due to too many failed login attempts"
        )
    
    # Verify password
    if not user.verify_password(form_data.password):
        user.increment_failed_login()
        db.commit()
        logger.warning(f"Failed login attempt for user: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create tokens
    access_token, refresh_token = create_token_pair(user.to_token_payload())
    
    # Store refresh token
    refresh_token_obj = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        device_info={"client": form_data.client_id} if form_data.client_id else {}
    )
    db.add(refresh_token_obj)
    
    # Update last login
    user.update_last_login()
    db.commit()
    
    logger.info(f"User logged in: {user.username}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    payload = verify_token(token_data.refresh_token, expected_type=TokenType.REFRESH)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if refresh token exists and is valid
    refresh_token_obj = db.query(RefreshToken).filter(
        RefreshToken.token == token_data.refresh_token
    ).first()
    
    if not refresh_token_obj or not refresh_token_obj.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user
    user = refresh_token_obj.user
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create new access token
    access_token = create_access_token(user.to_token_payload())
    
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user (revoke all refresh tokens)
    """
    # Revoke all user's refresh tokens
    refresh_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    ).all()
    
    for token in refresh_tokens:
        token.revoke()
    
    db.commit()
    
    logger.info(f"User logged out: {current_user.username}")
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the current user
    """
    # Generate API key
    api_key_plain = create_api_key()
    
    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
    
    # Create API key object
    api_key = APIKey(
        key=hash_api_key(api_key_plain),
        name=key_data.name,
        description=key_data.description,
        user_id=current_user.id,
        expires_at=expires_at,
        permissions=key_data.permissions or []
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    logger.info(f"API key created for user {current_user.username}: {api_key.name}")
    
    return APIKeyResponse(
        id=api_key.id,
        key=api_key_plain,  # Only returned on creation
        name=api_key.name,
        description=api_key.description,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user
    """
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).all()
    
    # Don't return the actual key values
    return [
        APIKeyResponse(
            id=key.id,
            key="***",  # Hide actual key
            name=key.name,
            description=key.description,
            expires_at=key.expires_at,
            created_at=key.created_at
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    db.commit()
    
    logger.info(f"API key revoked: {api_key.name} by user {current_user.username}")
    
    return {"message": "API key revoked successfully"}


@router.post("/request-password-reset")
async def request_password_reset(
    email: EmailStr = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Request a password reset token
    """
    user = db.query(User).filter(User.email == email).first()
    
    # Don't reveal if email exists or not
    if user:
        # Create reset token
        reset_token = create_access_token(
            {"sub": str(user.id), "email": user.email},
            token_type=TokenType.RESET_PASSWORD
        )
        
        # TODO: Send email with reset token
        logger.info(f"Password reset requested for user: {user.username}")
        
        # In production, don't return the token, send it via email
        # For now, return it for testing
        return {"message": "If the email exists, a reset link has been sent", "token": reset_token}
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset password using reset token
    """
    # Verify reset token
    payload = verify_token(reset_data.token, expected_type=TokenType.RESET_PASSWORD)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Set new password
    user.set_password(reset_data.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    
    # Revoke all refresh tokens (force re-login)
    refresh_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False
    ).all()
    
    for token in refresh_tokens:
        token.revoke()
    
    db.commit()
    
    logger.info(f"Password reset for user: {user.username}")
    
    return {"message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerification,
    db: Session = Depends(get_db)
):
    """
    Verify email address using verification token
    """
    # Verify token
    payload = verify_token(verification_data.token, expected_type=TokenType.EMAIL_VERIFICATION)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Get user
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Mark as verified
    user.is_verified = True
    db.commit()
    
    logger.info(f"Email verified for user: {user.username}")
    
    return {"message": "Email verified successfully"}


@router.post("/request-email-verification")
async def request_email_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request a new email verification token
    """
    if current_user.is_verified:
        return {"message": "Email already verified"}
    
    # Create verification token
    verification_token = create_access_token(
        {"sub": str(current_user.id), "email": current_user.email},
        token_type=TokenType.EMAIL_VERIFICATION
    )
    
    # TODO: Send email with verification token
    logger.info(f"Email verification requested for user: {current_user.username}")
    
    # In production, don't return the token, send it via email
    # For now, return it for testing
    return {"message": "Verification email sent", "token": verification_token}