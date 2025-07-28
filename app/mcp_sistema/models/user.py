"""
User model for authentication and authorization
"""
from sqlalchemy import Column, String, Boolean, Text, JSON, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .database import Base
from .base import BaseAuditModel, BaseSoftDeleteModel
from ..core.security import verify_password, get_password_hash


# Association tables for many-to-many relationships
user_roles = Table(
    'mcp_user_roles',
    Base.metadata,
    Column('user_id', ForeignKey('mcp_users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', ForeignKey('mcp_roles.id', ondelete='CASCADE'), primary_key=True)
)

user_permissions = Table(
    'mcp_user_permissions',
    Base.metadata,
    Column('user_id', ForeignKey('mcp_users.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', ForeignKey('mcp_permissions.id', ondelete='CASCADE'), primary_key=True)
)

role_permissions = Table(
    'mcp_role_permissions',
    Base.metadata,
    Column('role_id', ForeignKey('mcp_roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', ForeignKey('mcp_permissions.id', ondelete='CASCADE'), primary_key=True)
)


class User(BaseAuditModel, BaseSoftDeleteModel, Base):
    """User model for authentication"""
    __tablename__ = "mcp_users"
    
    # Basic info
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Security
    api_key = Column(String(255), unique=True, index=True)
    api_key_created_at = Column(DateTime(timezone=True))
    last_login = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    
    # MCP specific
    mcp_client_id = Column(String(255), unique=True, index=True)
    mcp_capabilities = Column(JSON, default=dict)
    
    # Additional data
    preferences = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users", lazy="selectin")
    permissions = relationship("Permission", secondary=user_permissions, back_populates="users", lazy="selectin")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("MCPSession", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str) -> None:
        """Hash and set password"""
        self.password_hash = get_password_hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return verify_password(password, self.password_hash)
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has specific permission (directly or through roles)"""
        # Check direct permissions
        if any(perm.name == permission_name for perm in self.permissions):
            return True
        
        # Check role permissions
        for role in self.roles:
            if any(perm.name == permission_name for perm in role.permissions):
                return True
        
        # Superuser has all permissions
        return self.is_superuser
    
    def get_all_permissions(self) -> List[str]:
        """Get all user permissions including role permissions"""
        permissions = set()
        
        # Direct permissions
        permissions.update(perm.name for perm in self.permissions)
        
        # Role permissions
        for role in self.roles:
            permissions.update(perm.name for perm in role.permissions)
        
        return list(permissions)
    
    def to_token_payload(self) -> Dict[str, Any]:
        """Generate JWT token payload"""
        return {
            "sub": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "roles": [role.name for role in self.roles],
            "permissions": self.get_all_permissions()
        }
    
    def update_last_login(self) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def increment_failed_login(self) -> None:
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class Role(BaseAuditModel, Base):
    """Role model for RBAC"""
    __tablename__ = "mcp_roles"
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles can't be deleted
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles", lazy="selectin")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(BaseAuditModel, Base):
    """Permission model for fine-grained access control"""
    __tablename__ = "mcp_permissions"
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(100), nullable=False, index=True)  # e.g., 'freight', 'user', 'report'
    action = Column(String(50), nullable=False, index=True)     # e.g., 'create', 'read', 'update', 'delete'
    description = Column(Text)
    is_system = Column(Boolean, default=False, nullable=False)   # System permissions can't be deleted
    
    # Relationships
    users = relationship("User", secondary=user_permissions, back_populates="permissions")
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    @classmethod
    def create_name(cls, resource: str, action: str) -> str:
        """Create permission name from resource and action"""
        return f"{resource}:{action}"
    
    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"


class RefreshToken(BaseAuditModel, Base):
    """Refresh token model for JWT authentication"""
    __tablename__ = "mcp_refresh_tokens"
    
    token = Column(String(500), unique=True, nullable=False, index=True)
    user_id = Column(ForeignKey('mcp_users.id', ondelete='CASCADE'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    device_info = Column(JSON, default=dict)  # Store device/client info
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    
    def is_valid(self) -> bool:
        """Check if token is valid"""
        if self.revoked:
            return False
        if self.expires_at < datetime.utcnow():
            return False
        return True
    
    def revoke(self) -> None:
        """Revoke the token"""
        self.revoked = True
        self.revoked_at = datetime.utcnow()
    
    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class APIKey(BaseAuditModel, Base):
    """API Key model for service authentication"""
    __tablename__ = "mcp_api_keys"
    
    key = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    user_id = Column(ForeignKey('mcp_users.id', ondelete='CASCADE'), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    permissions = Column(JSON, default=list)  # List of allowed permissions
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Relationships
    user = relationship("User", backref="api_keys")
    
    def is_valid(self) -> bool:
        """Check if API key is valid"""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def update_last_used(self) -> None:
        """Update last used timestamp"""
        self.last_used_at = datetime.utcnow()
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, user_id={self.user_id})>"