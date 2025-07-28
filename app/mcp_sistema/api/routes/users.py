"""
User management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
import logging

from ...models.database import get_db
from ...models.user import User, Role, Permission
from ..dependencies.auth import (
    get_current_active_user,
    require_admin,
    require_superuser,
    require_permission,
    get_security_context
)
from ...core.security import get_password_hash, generate_secure_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# Pydantic models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    roles: List[str] = []


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    roles: Optional[List[str]] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    is_superuser: bool
    roles: List[str]
    permissions: List[str]
    created_at: str
    updated_at: Optional[str]
    last_login: Optional[str]
    
    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = []


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_system: bool
    permissions: List[str]
    user_count: int
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: int
    name: str
    resource: str
    action: str
    description: Optional[str]
    is_system: bool
    
    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search by username or email"),
    is_active: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("user:read")),
    db: Session = Depends(get_db)
):
    """
    List all users (requires user:read permission)
    """
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if role:
        query = query.join(User.roles).filter(Role.name == role)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    
    # Convert to response
    response = []
    for user in users:
        response.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            roles=[role.name for role in user.roles],
            permissions=user.get_all_permissions(),
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat() if user.updated_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None
        ))
    
    return response


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission("user:create")),
    db: Session = Depends(get_db)
):
    """
    Create a new user (requires user:create permission)
    """
    # Check if username or email already exists
    existing = db.query(User).filter(
        or_(
            User.username == user_data.username,
            User.email == user_data.email
        )
    ).first()
    
    if existing:
        if existing.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        is_active=user_data.is_active,
        is_verified=user_data.is_verified,
        created_by=current_user.username
    )
    
    # Set password (generate if not provided)
    if user_data.password:
        user.set_password(user_data.password)
    else:
        temp_password = generate_secure_password()
        user.set_password(temp_password)
        # TODO: Send temp password via email
        logger.info(f"Generated temporary password for user {user.username}")
    
    # Assign roles
    for role_name in user_data.roles:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role:
            user.roles.append(role)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User created: {user.username} by {current_user.username}")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        permissions=user.get_all_permissions(),
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
        last_login=None
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("user:read")),
    db: Session = Depends(get_db)
):
    """
    Get user by ID (requires user:read permission)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        permissions=user.get_all_permissions(),
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_permission("user:update")),
    db: Session = Depends(get_db)
):
    """
    Update user (requires user:update permission)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.email is not None:
        # Check if email is already taken
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = user_update.email
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    if user_update.is_verified is not None:
        user.is_verified = user_update.is_verified
    
    if user_update.roles is not None:
        # Clear existing roles
        user.roles.clear()
        
        # Add new roles
        for role_name in user_update.roles:
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                user.roles.append(role)
    
    user.updated_by = current_user.username
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User updated: {user.username} by {current_user.username}")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        roles=[role.name for role in user.roles],
        permissions=user.get_all_permissions(),
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission("user:delete")),
    db: Session = Depends(get_db)
):
    """
    Delete user (requires user:delete permission)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting superuser
    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete superuser"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Soft delete
    user.soft_delete()
    user.updated_by = current_user.username
    
    db.commit()
    
    logger.info(f"User deleted: {user.username} by {current_user.username}")
    
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    current_user: User = Depends(require_permission("user:update")),
    db: Session = Depends(get_db)
):
    """
    Reset user password (requires user:update permission)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate new password
    new_password = generate_secure_password()
    user.set_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_by = current_user.username
    
    db.commit()
    
    logger.info(f"Password reset for user: {user.username} by {current_user.username}")
    
    # TODO: Send new password via email
    # For now, return it (remove in production)
    return {
        "message": "Password reset successfully",
        "temporary_password": new_password  # Remove this in production
    }


@router.post("/me/change-password")
async def change_my_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password
    """
    # Verify current password
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Set new password
    current_user.set_password(password_data.new_password)
    
    db.commit()
    
    logger.info(f"Password changed for user: {current_user.username}")
    
    return {"message": "Password changed successfully"}


# Role endpoints
@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(require_permission("role:read")),
    db: Session = Depends(get_db)
):
    """
    List all roles (requires role:read permission)
    """
    roles = db.query(Role).all()
    
    response = []
    for role in roles:
        response.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=[perm.name for perm in role.permissions],
            user_count=len(role.users)
        ))
    
    return response


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_permission("role:create")),
    db: Session = Depends(get_db)
):
    """
    Create a new role (requires role:create permission)
    """
    # Check if role already exists
    existing = db.query(Role).filter(Role.name == role_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists"
        )
    
    # Create role
    role = Role(
        name=role_data.name,
        description=role_data.description,
        created_by=current_user.username
    )
    
    # Add permissions
    for perm_name in role_data.permissions:
        permission = db.query(Permission).filter(Permission.name == perm_name).first()
        if permission:
            role.permissions.append(permission)
    
    db.add(role)
    db.commit()
    db.refresh(role)
    
    logger.info(f"Role created: {role.name} by {current_user.username}")
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[perm.name for perm in role.permissions],
        user_count=0
    )


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_update: RoleUpdate,
    current_user: User = Depends(require_permission("role:update")),
    db: Session = Depends(get_db)
):
    """
    Update role (requires role:update permission)
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Prevent updating system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system role"
        )
    
    # Update fields
    if role_update.description is not None:
        role.description = role_update.description
    
    if role_update.permissions is not None:
        # Clear existing permissions
        role.permissions.clear()
        
        # Add new permissions
        for perm_name in role_update.permissions:
            permission = db.query(Permission).filter(Permission.name == perm_name).first()
            if permission:
                role.permissions.append(permission)
    
    role.updated_by = current_user.username
    
    db.commit()
    db.refresh(role)
    
    logger.info(f"Role updated: {role.name} by {current_user.username}")
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[perm.name for perm in role.permissions],
        user_count=len(role.users)
    )


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_permission("role:delete")),
    db: Session = Depends(get_db)
):
    """
    Delete role (requires role:delete permission)
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Prevent deleting system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system role"
        )
    
    # Check if role has users
    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role with {len(role.users)} users"
        )
    
    db.delete(role)
    db.commit()
    
    logger.info(f"Role deleted: {role.name} by {current_user.username}")
    
    return {"message": "Role deleted successfully"}


# Permission endpoints
@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("permission:read")),
    db: Session = Depends(get_db)
):
    """
    List all permissions (requires permission:read permission)
    """
    query = db.query(Permission)
    
    if resource:
        query = query.filter(Permission.resource == resource)
    
    if action:
        query = query.filter(Permission.action == action)
    
    permissions = query.all()
    
    return [
        PermissionResponse(
            id=perm.id,
            name=perm.name,
            resource=perm.resource,
            action=perm.action,
            description=perm.description,
            is_system=perm.is_system
        )
        for perm in permissions
    ]