"""
Unified Permission Decorator System
===================================

This module provides a unified decorator that supports both legacy and new 
hierarchical permission formats, ensuring backward compatibility while 
enabling advanced permission management.
"""

from functools import wraps
from flask import abort, redirect, url_for, flash, request, g
from flask_login import current_user
from app.permissions.models import (
    LogPermissao, ModuloSistema, FuncaoModulo, PermissionSubModule,
    PermissionCategory, PermissionModule, UserPermission
)
from app.permissions.cache import PermissionCache
import logging
from typing import Optional, Union, List, Dict, Any
import hashlib
import json

logger = logging.getLogger(__name__)

class PermissionChecker:
    """
    Unified permission checker that handles both legacy and new formats
    """
    
    def __init__(self):
        self.cache = PermissionCache()
    
    def check_permission(
        self,
        user,
        module: str,
        function: Optional[str] = None,
        submodule: Optional[str] = None,
        category: Optional[str] = None,
        action: str = 'view',  # 'view' or 'edit'
        use_cache: bool = True
    ) -> bool:
        """
        Check if user has permission using unified logic
        
        Args:
            user: User object
            module: Module name (required)
            function: Function name (optional)
            submodule: Submodule name (optional)
            category: Category name (optional)
            action: Permission action ('view' or 'edit')
            use_cache: Whether to use cache
            
        Returns:
            bool: True if user has permission
        """
        if not user or not user.is_authenticated:
            return False
        
        # Admin always has access
        if user.perfil == 'administrador':
            return True
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            user.id, module, function, submodule, category, action
        )
        
        # Check cache if enabled
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Permission cache hit for key: {cache_key}")
                return cached_result
        
        # Determine which system to use
        if self._is_legacy_format(module, function, submodule, category):
            result = self._check_legacy_permission(user, module, action)
        else:
            result = self._check_hierarchical_permission(
                user, module, function, submodule, category, action
            )
        
        # Cache result
        if use_cache:
            self.cache.set(cache_key, result, ttl=300)  # 5 minutes
        
        return result
    
    def _generate_cache_key(
        self,
        user_id: int,
        module: str,
        function: Optional[str],
        submodule: Optional[str],
        category: Optional[str],
        action: str
    ) -> str:
        """Generate a cache key for permission check"""
        components = [
            str(user_id),
            module or '',
            function or '',
            submodule or '',
            category or '',
            action
        ]
        key_string = ':'.join(components)
        return f"perm:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _is_legacy_format(
        self,
        module: str,
        function: Optional[str],
        submodule: Optional[str],
        category: Optional[str]
    ) -> bool:
        """
        Determine if this is using legacy format
        Legacy format: Only module specified, or module doesn't exist in new system
        """
        # If category is specified, it's definitely new format
        if category:
            return False
        
        # Check if module exists in new hierarchical system
        new_module = PermissionModule.query.filter_by(
            name=module, active=True
        ).first()
        
        # If not in new system, use legacy
        if not new_module:
            return True
        
        # If only module specified (no function/submodule), check if it's a legacy call
        if not function and not submodule:
            # Check if there are old-style permissions for this module
            old_module = ModuloSistema.query.filter_by(
                nome=module, ativo=True
            ).first()
            return old_module is not None
        
        return False
    
    def _check_legacy_permission(
        self,
        user,
        module: str,
        action: str
    ) -> bool:
        """Check permission using legacy system"""
        if action == 'edit':
            return user.pode_editar(module)
        else:
            return user.tem_permissao(module)
    
    def _check_hierarchical_permission(
        self,
        user,
        module: str,
        function: Optional[str],
        submodule: Optional[str],
        category: Optional[str],
        action: str
    ) -> bool:
        """Check permission using new hierarchical system"""
        # Find the most specific entity
        entity_type, entity_id = self._find_permission_entity(
            category, module, submodule, function
        )
        
        if not entity_id:
            return False
        
        # Check user permission at this level
        permission = UserPermission.query.filter_by(
            user_id=user.id,
            entity_type=entity_type,
            entity_id=entity_id,
            active=True
        ).first()
        
        if permission and not permission.is_expired:
            if action == 'edit':
                return permission.can_edit
            else:
                return permission.can_view
        
        # Check cascade permissions (parent levels)
        return self._check_cascade_permissions(
            user, entity_type, entity_id, action
        )
    
    def _find_permission_entity(
        self,
        category: Optional[str],
        module: str,
        submodule: Optional[str],
        function: Optional[str]
    ) -> tuple[Optional[str], Optional[int]]:
        """Find the most specific permission entity"""
        # Try submodule level first (most specific)
        if submodule and function:
            sub = PermissionSubModule.query.join(
                PermissionModule
            ).filter(
                PermissionModule.name == module,
                PermissionSubModule.name == submodule,
                PermissionSubModule.active == True
            ).first()
            if sub:
                return 'SUBMODULE', sub.id
        
        # Try module level
        if module:
            mod = PermissionModule.query.filter_by(
                name=module, active=True
            ).first()
            if mod:
                return 'MODULE', mod.id
        
        # Try category level
        if category:
            cat = PermissionCategory.query.filter_by(
                name=category, active=True
            ).first()
            if cat:
                return 'CATEGORY', cat.id
        
        return None, None
    
    def _check_cascade_permissions(
        self,
        user,
        entity_type: str,
        entity_id: int,
        action: str
    ) -> bool:
        """Check cascade permissions from parent entities"""
        # Get parent hierarchy
        parents = self._get_parent_entities(entity_type, entity_id)
        
        for parent_type, parent_id in parents:
            permission = UserPermission.query.filter_by(
                user_id=user.id,
                entity_type=parent_type,
                entity_id=parent_id,
                active=True
            ).first()
            
            if permission and not permission.is_expired:
                # Check if this permission has cascade disabled
                if permission.custom_override:
                    continue
                
                if action == 'edit':
                    if permission.can_edit:
                        return True
                else:
                    if permission.can_view:
                        return True
        
        return False
    
    def _get_parent_entities(
        self,
        entity_type: str,
        entity_id: int
    ) -> List[tuple[str, int]]:
        """Get parent entities for cascade checking"""
        parents = []
        
        if entity_type == 'SUBMODULE':
            # Get parent module
            sub = PermissionSubModule.query.get(entity_id)
            if sub:
                parents.append(('MODULE', sub.module_id))
                # Get parent category
                if sub.module.category_id:
                    parents.append(('CATEGORY', sub.module.category_id))
        
        elif entity_type == 'MODULE':
            # Get parent category
            mod = PermissionModule.query.get(entity_id)
            if mod and mod.category_id:
                parents.append(('CATEGORY', mod.category_id))
        
        return parents


# Global permission checker instance
permission_checker = PermissionChecker()


def check_permission(
    module: str = None,
    function: str = None,
    submodule: str = None,
    category: str = None,
    action: str = 'view',
    redirect_on_fail: bool = True,
    message: str = None,
    legacy_mode: bool = False
):
    """
    Unified permission decorator supporting both legacy and new formats
    
    Args:
        module: Module name (required for legacy, optional for new)
        function: Function name (optional)
        submodule: Submodule name (optional)
        category: Category name (optional)
        action: Permission action ('view' or 'edit')
        redirect_on_fail: Whether to redirect on permission failure
        message: Custom error message
        legacy_mode: Force legacy mode checking
    
    Examples:
        # Legacy format
        @check_permission(module='faturamento')
        @check_permission(module='faturamento', function='listar')
        
        # New hierarchical format
        @check_permission(category='financeiro', module='faturamento', submodule='faturas', function='listar')
        @check_permission(module='faturamento', submodule='faturas', action='edit')
        
        # Force legacy mode
        @check_permission(module='faturamento', legacy_mode=True)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                if redirect_on_fail:
                    flash('Por favor, faça login para acessar esta página.', 'warning')
                    return redirect(url_for('auth.login'))
                abort(401)
            
            # Force legacy mode if specified
            if legacy_mode:
                has_permission = permission_checker._check_legacy_permission(
                    current_user, module, action
                )
            else:
                # Use unified checker
                has_permission = permission_checker.check_permission(
                    current_user, module, function, submodule, category, action
                )
            
            # Log the access attempt
            log_details = {
                'module': module,
                'function': function,
                'submodule': submodule,
                'category': category,
                'action': action,
                'legacy_mode': legacy_mode,
                'route': request.endpoint,
                'method': request.method
            }
            
            if not has_permission:
                # Log denied access
                LogPermissao.registrar(
                    usuario_id=current_user.id,
                    acao='TENTATIVA_NEGADA',
                    detalhes=json.dumps(log_details),
                    resultado='NEGADO',
                    ip_origem=request.remote_addr,
                    user_agent=request.user_agent.string,
                    sessao_id=request.headers.get('X-Session-ID')
                )
                
                # Handle denial
                if redirect_on_fail:
                    error_msg = message or f'Você não tem permissão para {action} este recurso.'
                    flash(error_msg, 'danger')
                    return redirect(url_for('main.index'))
                abort(403)
            
            # Log successful access
            LogPermissao.registrar(
                usuario_id=current_user.id,
                acao='USADA',
                detalhes=json.dumps(log_details),
                resultado='SUCESSO',
                ip_origem=request.remote_addr,
                user_agent=request.user_agent.string,
                sessao_id=request.headers.get('X-Session-ID')
            )
            
            # Add permission info to g object for use in templates
            if not hasattr(g, 'user_permissions'):
                g.user_permissions = {}
            
            permission_key = f"{module or ''}.{function or ''}.{submodule or ''}"
            g.user_permissions[permission_key] = {
                'can_view': has_permission,
                'can_edit': action == 'edit' and has_permission
            }
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Backward compatibility aliases
def requer_permissao(modulo, funcao=None, submodulo=None, redirecionar=True):
    """Legacy decorator for backward compatibility"""
    return check_permission(
        module=modulo,
        function=funcao,
        submodule=submodulo,
        redirect_on_fail=redirecionar,
        legacy_mode=True
    )


def requer_edicao(modulo, funcao=None, submodulo=None, redirecionar=True):
    """Legacy decorator for edit permissions"""
    return check_permission(
        module=modulo,
        function=funcao,
        submodule=submodulo,
        action='edit',
        redirect_on_fail=redirecionar,
        legacy_mode=True
    )


# Template helpers
def can_access(module: str, function: str = None, submodule: str = None, 
               category: str = None, action: str = 'view') -> bool:
    """
    Template helper to check permissions
    
    Usage in templates:
        {% if can_access('faturamento', 'listar') %}
            <a href="/faturamento/listar">Listar Faturas</a>
        {% endif %}
    """
    if not current_user.is_authenticated:
        return False
    
    return permission_checker.check_permission(
        current_user, module, function, submodule, category, action
    )


def get_user_permissions() -> Dict[str, Any]:
    """Get all permissions for current user in a structured format"""
    if not current_user.is_authenticated:
        return {}
    
    # This would be implemented to return a structured permission tree
    # For now, return from g object if available
    return getattr(g, 'user_permissions', {})


# Import the fixed require_permission for backward compatibility
try:
    from .decorators_fix import require_permission, require_admin_new
    logger.info("✅ Loaded fixed require_permission decorator")
except ImportError:
    logger.warning("⚠️ Could not load fixed require_permission decorator")
    # Fallback to simple wrapper
    def require_permission(*args, **kwargs):
        """Emergency fallback wrapper"""
        if len(args) == 3:
            # Old format
            module, function, level = args
            return check_permission(module=module, function=function, action='edit' if level == 'editar' else 'view')
        elif len(args) == 1:
            # New format
            return check_permission(module=args[0])
        else:
            raise TypeError(f"require_permission() takes 1 or 3 arguments, got {len(args)}")
    
    require_admin_new = require_permission