"""
Permission Management API
========================

RESTful API endpoints for managing user permissions, templates, and batch operations.
"""

from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from app import db
from app.permissions.models import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate, ModuloSistema, FuncaoModulo,
    PermissaoUsuario, UsuarioVendedor, UsuarioEquipeVendas,
    LogPermissao, BatchPermissionOperation
)
from app.permissions.decorators import check_permission
from app.permissions.cache import invalidate_user_permissions, invalidate_module_permissions
from app.auth.models import Usuario
from app.utils.timezone import agora_brasil
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

# Create blueprint
permissions_api = Blueprint('permissions_api', __name__, url_prefix='/api/v1/permissions')

# Error handlers
@permissions_api.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400

@permissions_api.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource'}), 403

@permissions_api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404

# Helper functions
def build_permission_tree():
    """Build hierarchical permission tree"""
    tree = []
    
    # Get all categories
    categories = PermissionCategory.query.filter_by(active=True).order_by(PermissionCategory.order_index).all()
    
    for category in categories:
        category_node = {
            'id': category.id,
            'name': category.name,
            'display_name': category.display_name,
            'description': category.description,
            'icon': category.icon,
            'color': category.color,
            'modules': []
        }
        
        # Get modules for this category
        modules = PermissionModule.query.filter_by(
            category_id=category.id,
            active=True
        ).order_by(PermissionModule.order_index).all()
        
        for module in modules:
            module_node = {
                'id': module.id,
                'name': module.name,
                'display_name': module.display_name,
                'description': module.description,
                'icon': module.icon,
                'color': module.color,
                'submodules': []
            }
            
            # Get submodules for this module
            submodules = PermissionSubModule.query.filter_by(
                module_id=module.id,
                active=True
            ).order_by(PermissionSubModule.order_index).all()
            
            for submodule in submodules:
                submodule_node = {
                    'id': submodule.id,
                    'name': submodule.name,
                    'display_name': submodule.display_name,
                    'description': submodule.description,
                    'route_pattern': submodule.route_pattern,
                    'critical_level': submodule.critical_level
                }
                module_node['submodules'].append(submodule_node)
            
            category_node['modules'].append(module_node)
        
        tree.append(category_node)
    
    # Add legacy modules without category
    legacy_modules = ModuloSistema.query.filter_by(ativo=True).all()
    legacy_node = {
        'id': 'legacy',
        'name': 'legacy',
        'display_name': 'Módulos Legados',
        'description': 'Módulos do sistema anterior',
        'icon': '📦',
        'color': '#6c757d',
        'modules': []
    }
    
    for module in legacy_modules:
        if not PermissionModule.query.filter_by(name=module.nome).first():
            module_node = {
                'id': f'legacy_{module.id}',
                'name': module.nome,
                'display_name': module.nome_exibicao,
                'description': module.descricao,
                'icon': module.icone,
                'color': module.cor,
                'legacy': True,
                'functions': []
            }
            
            # Get functions
            functions = FuncaoModulo.query.filter_by(
                modulo_id=module.id,
                ativo=True
            ).order_by(FuncaoModulo.ordem).all()
            
            for func in functions:
                func_node = {
                    'id': func.id,
                    'name': func.nome,
                    'display_name': func.nome_exibicao,
                    'description': func.descricao,
                    'route': func.rota_padrao,
                    'critical_level': func.nivel_critico
                }
                module_node['functions'].append(func_node)
            
            legacy_node['modules'].append(module_node)
    
    if legacy_node['modules']:
        tree.append(legacy_node)
    
    return tree


def get_user_permissions_tree(user_id):
    """Get permission tree with user's current permissions"""
    tree = build_permission_tree()
    
    # Get user's hierarchical permissions
    user_perms = UserPermission.query.filter_by(
        user_id=user_id,
        active=True
    ).all()
    
    # Create lookup dict
    perm_lookup = {}
    for perm in user_perms:
        key = f"{perm.entity_type}_{perm.entity_id}"
        perm_lookup[key] = {
            'can_view': perm.can_view,
            'can_edit': perm.can_edit,
            'can_delete': perm.can_delete,
            'can_export': perm.can_export,
            'custom_override': perm.custom_override,
            'expires_at': perm.expires_at.isoformat() if perm.expires_at else None
        }
    
    # Get legacy permissions
    legacy_perms = PermissaoUsuario.query.filter_by(
        usuario_id=user_id,
        ativo=True
    ).all()
    
    legacy_lookup = {}
    for perm in legacy_perms:
        legacy_lookup[perm.funcao_id] = {
            'can_view': perm.pode_visualizar,
            'can_edit': perm.pode_editar,
            'expires_at': perm.expira_em.isoformat() if perm.expira_em else None
        }
    
    # Add permission info to tree
    for category in tree:
        if category['id'] != 'legacy':
            category['permissions'] = perm_lookup.get(f"CATEGORY_{category['id']}", {})
        
        for module in category['modules']:
            if 'legacy' in str(module['id']):
                # Legacy module - check functions
                if 'functions' in module:
                    for func in module['functions']:
                        func['permissions'] = legacy_lookup.get(func['id'], {})
            else:
                module['permissions'] = perm_lookup.get(f"MODULE_{module['id']}", {})
                
                if 'submodules' in module:
                    for submodule in module['submodules']:
                        submodule['permissions'] = perm_lookup.get(f"SUBMODULE_{submodule['id']}", {})
    
    return tree


# API Endpoints

@permissions_api.route('/categories', methods=['GET'])
@login_required
@check_permission(module='admin', function='permissoes')
def list_categories():
    """List all permission categories with modules and submodules"""
    try:
        tree = build_permission_tree()
        return jsonify({
            'success': True,
            'data': tree
        })
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@permissions_api.route('/user/<int:user_id>/permissions', methods=['GET'])
@login_required
@check_permission(module='usuarios', function='permissoes')
def get_user_permissions(user_id):
    """Get all permissions for a specific user"""
    try:
        # Check if user exists
        user = Usuario.query.get_or_404(user_id)
        
        # Get permission tree with user's permissions
        tree = get_user_permissions_tree(user_id)
        
        # Get additional user info
        user_info = {
            'id': user.id,
            'name': user.nome,
            'email': user.email,
            'profile': user.perfil,
            'vendors': UsuarioVendedor.get_vendedores_usuario(user_id),
            'teams': UsuarioEquipeVendas.get_equipes_usuario(user_id)
        }
        
        return jsonify({
            'success': True,
            'user': user_info,
            'permissions': tree
        })
        
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@permissions_api.route('/user/<int:user_id>/permissions', methods=['POST'])
@login_required
@check_permission(module='usuarios', function='permissoes', action='edit')
def update_user_permissions(user_id):
    """Update user permissions"""
    try:
        data = request.get_json()
        if not data:
            abort(400, "No data provided")
        
        # Verify user exists
        user = Usuario.query.get_or_404(user_id)
        
        # Start batch operation
        batch_op = BatchPermissionOperation(
            operation_type='UPDATE',
            description=f'Update permissions for user {user.nome}',
            executed_by=current_user.id,
            status='IN_PROGRESS'
        )
        db.session.add(batch_op)
        db.session.flush()
        
        success_count = 0
        error_count = 0
        errors = []
        
        # Process permission updates
        permissions = data.get('permissions', [])
        for perm_data in permissions:
            try:
                entity_type = perm_data.get('entity_type')
                entity_id = perm_data.get('entity_id')
                
                if not entity_type or not entity_id:
                    errors.append("Missing entity type or ID")
                    error_count += 1
                    continue
                
                # Find or create permission
                permission = UserPermission.query.filter_by(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id
                ).first()
                
                if not permission:
                    permission = UserPermission(
                        user_id=user_id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        granted_by=current_user.id
                    )
                
                # Update permission
                permission.can_view = perm_data.get('can_view', False)
                permission.can_edit = perm_data.get('can_edit', False)
                permission.can_delete = perm_data.get('can_delete', False)
                permission.can_export = perm_data.get('can_export', False)
                permission.custom_override = perm_data.get('custom_override', False)
                permission.active = perm_data.get('active', True)
                
                # Handle expiration
                if 'expires_in_days' in perm_data:
                    days = perm_data['expires_in_days']
                    if days:
                        permission.expires_at = agora_brasil() + timedelta(days=days)
                    else:
                        permission.expires_at = None
                
                db.session.add(permission)
                success_count += 1
                
            except Exception as e:
                errors.append(str(e))
                error_count += 1
        
        # Update batch operation
        batch_op.affected_permissions = success_count
        batch_op.status = 'COMPLETED' if error_count == 0 else 'COMPLETED_WITH_ERRORS'
        batch_op.completed_at = agora_brasil()
        batch_op.details = {
            'success': success_count,
            'errors': error_count,
            'error_details': errors[:10]  # Limit error details
        }
        
        db.session.commit()
        
        # Invalidate cache for this user
        invalidate_user_permissions(user_id)
        
        # Log the change
        LogPermissao.registrar(
            usuario_id=current_user.id,
            acao='PERMISSOES_ATUALIZADAS',
            detalhes=json.dumps({
                'target_user': user_id,
                'changes': len(permissions),
                'success': success_count,
                'errors': error_count
            }),
            resultado='SUCESSO' if error_count == 0 else 'PARCIAL',
            ip_origem=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        return jsonify({
            'success': True,
            'message': f'Permissions updated: {success_count} successful, {error_count} errors',
            'details': {
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating user permissions: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@permissions_api.route('/templates', methods=['GET'])
@login_required
@check_permission(module='usuarios', function='permissoes')
def list_templates():
    """List available permission templates"""
    try:
        templates = PermissionTemplate.query.filter_by(active=True).all()
        
        template_list = []
        for template in templates:
            template_list.append({
                'id': template.id,
                'name': template.name,
                'code': template.code,
                'description': template.description,
                'category': template.category,
                'is_system': template.is_system,
                'created_at': template.created_at.isoformat(),
                'permissions': template.get_permissions()
            })
        
        return jsonify({
            'success': True,
            'data': template_list
        })
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@permissions_api.route('/templates/<int:template_id>/apply', methods=['POST'])
@login_required
@check_permission(module='usuarios', function='permissoes', action='edit')
def apply_template(template_id):
    """Apply a permission template to users"""
    try:
        data = request.get_json()
        if not data:
            abort(400, "No data provided")
        
        user_ids = data.get('user_ids', [])
        if not user_ids:
            abort(400, "No users specified")
        
        # Get template
        template = PermissionTemplate.query.get_or_404(template_id)
        if not template.active:
            abort(400, "Template is not active")
        
        # Apply template to each user
        success_count = 0
        error_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                user = Usuario.query.get(user_id)
                if not user:
                    errors.append(f"User {user_id} not found")
                    error_count += 1
                    continue
                
                # Apply template
                if user.aplicar_template_permissao(template_id, current_user.id):
                    success_count += 1
                    invalidate_user_permissions(user_id)
                else:
                    errors.append(f"Failed to apply template to user {user_id}")
                    error_count += 1
                    
            except Exception as e:
                errors.append(f"Error for user {user_id}: {str(e)}")
                error_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Template applied: {success_count} successful, {error_count} errors',
            'details': {
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
        })
        
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@permissions_api.route('/batch', methods=['POST'])
@login_required
@check_permission(module='usuarios', function='permissoes', action='edit')
def batch_operation():
    """Execute batch permission operations"""
    try:
        data = request.get_json()
        if not data:
            abort(400, "No data provided")
        
        operation = data.get('operation')  # GRANT, REVOKE, COPY
        if operation not in ['GRANT', 'REVOKE', 'COPY']:
            abort(400, "Invalid operation")
        
        # Create batch operation record
        batch_op = BatchPermissionOperation(
            operation_type=operation,
            description=data.get('description', f'Batch {operation} operation'),
            executed_by=current_user.id,
            status='IN_PROGRESS'
        )
        db.session.add(batch_op)
        db.session.flush()
        
        try:
            if operation == 'GRANT':
                result = _batch_grant(data, batch_op)
            elif operation == 'REVOKE':
                result = _batch_revoke(data, batch_op)
            elif operation == 'COPY':
                result = _batch_copy(data, batch_op)
            
            # Update batch operation
            batch_op.affected_users = result['affected_users']
            batch_op.affected_permissions = result['affected_permissions']
            batch_op.status = 'COMPLETED' if result['error_count'] == 0 else 'COMPLETED_WITH_ERRORS'
            batch_op.completed_at = agora_brasil()
            batch_op.details = result
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'batch_id': batch_op.id,
                'result': result
            })
            
        except Exception as e:
            batch_op.status = 'FAILED'
            batch_op.error_details = str(e)
            db.session.commit()
            raise
        
    except Exception as e:
        logger.error(f"Error in batch operation: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _batch_grant(data, batch_op):
    """Execute batch grant operation"""
    user_ids = data.get('user_ids', [])
    permissions = data.get('permissions', [])
    
    success_count = 0
    error_count = 0
    errors = []
    
    for user_id in user_ids:
        for perm in permissions:
            try:
                # Create or update permission
                entity_type = perm['entity_type']
                entity_id = perm['entity_id']
                
                user_perm = UserPermission.query.filter_by(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id
                ).first()
                
                if not user_perm:
                    user_perm = UserPermission(
                        user_id=user_id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        granted_by=current_user.id
                    )
                
                user_perm.can_view = perm.get('can_view', True)
                user_perm.can_edit = perm.get('can_edit', False)
                user_perm.can_delete = perm.get('can_delete', False)
                user_perm.can_export = perm.get('can_export', False)
                user_perm.active = True
                
                db.session.add(user_perm)
                success_count += 1
                
            except Exception as e:
                errors.append(str(e))
                error_count += 1
    
    # Invalidate cache for all affected users
    for user_id in user_ids:
        invalidate_user_permissions(user_id)
    
    return {
        'affected_users': len(user_ids),
        'affected_permissions': success_count,
        'error_count': error_count,
        'errors': errors[:10]
    }


def _batch_revoke(data, batch_op):
    """Execute batch revoke operation"""
    user_ids = data.get('user_ids', [])
    entity_types = data.get('entity_types', [])
    entity_ids = data.get('entity_ids', [])
    
    # Build query
    query = UserPermission.query.filter(
        UserPermission.user_id.in_(user_ids)
    )
    
    if entity_types:
        query = query.filter(UserPermission.entity_type.in_(entity_types))
    
    if entity_ids:
        query = query.filter(UserPermission.entity_id.in_(entity_ids))
    
    # Deactivate permissions
    affected = query.update({'active': False}, synchronize_session=False)
    
    # Invalidate cache
    for user_id in user_ids:
        invalidate_user_permissions(user_id)
    
    return {
        'affected_users': len(user_ids),
        'affected_permissions': affected,
        'error_count': 0,
        'errors': []
    }


def _batch_copy(data, batch_op):
    """Execute batch copy operation (copy permissions from one user to others)"""
    source_user_id = data.get('source_user_id')
    target_user_ids = data.get('target_user_ids', [])
    
    if not source_user_id:
        raise ValueError("Source user ID required")
    
    # Get source user permissions
    source_perms = UserPermission.query.filter_by(
        user_id=source_user_id,
        active=True
    ).all()
    
    success_count = 0
    error_count = 0
    errors = []
    
    for target_id in target_user_ids:
        for source_perm in source_perms:
            try:
                # Check if permission already exists
                existing = UserPermission.query.filter_by(
                    user_id=target_id,
                    entity_type=source_perm.entity_type,
                    entity_id=source_perm.entity_id
                ).first()
                
                if not existing:
                    # Create new permission
                    new_perm = UserPermission(
                        user_id=target_id,
                        entity_type=source_perm.entity_type,
                        entity_id=source_perm.entity_id,
                        can_view=source_perm.can_view,
                        can_edit=source_perm.can_edit,
                        can_delete=source_perm.can_delete,
                        can_export=source_perm.can_export,
                        custom_override=source_perm.custom_override,
                        granted_by=current_user.id,
                        active=True
                    )
                    db.session.add(new_perm)
                else:
                    # Update existing
                    existing.can_view = source_perm.can_view
                    existing.can_edit = source_perm.can_edit
                    existing.can_delete = source_perm.can_delete
                    existing.can_export = source_perm.can_export
                    existing.custom_override = source_perm.custom_override
                    existing.active = True
                
                success_count += 1
                
            except Exception as e:
                errors.append(str(e))
                error_count += 1
    
    # Invalidate cache
    for user_id in target_user_ids:
        invalidate_user_permissions(user_id)
    
    return {
        'affected_users': len(target_user_ids),
        'affected_permissions': success_count,
        'error_count': error_count,
        'errors': errors[:10]
    }


@permissions_api.route('/audit/logs', methods=['GET'])
@login_required
@check_permission(module='admin', function='logs')
def get_audit_logs():
    """Get permission audit logs"""
    try:
        # Get query parameters
        user_id = request.args.get('user_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        action = request.args.get('action')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = LogPermissao.query
        
        if user_id:
            query = query.filter_by(usuario_id=user_id)
        
        if action:
            query = query.filter_by(acao=action)
        
        if date_from:
            query = query.filter(LogPermissao.timestamp >= datetime.fromisoformat(date_from))
        
        if date_to:
            query = query.filter(LogPermissao.timestamp <= datetime.fromisoformat(date_to))
        
        # Get total count
        total = query.count()
        
        # Get logs
        logs = query.order_by(LogPermissao.timestamp.desc())\
                   .limit(limit)\
                   .offset(offset)\
                   .all()
        
        # Format logs
        log_list = []
        for log in logs:
            log_list.append({
                'id': log.id,
                'user_id': log.usuario_id,
                'user_name': log.usuario.nome if log.usuario else 'Unknown',
                'action': log.acao,
                'details': json.loads(log.detalhes) if log.detalhes else {},
                'result': log.resultado,
                'ip_address': log.ip_origem,
                'user_agent': log.user_agent,
                'timestamp': log.timestamp.isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': log_list,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@permissions_api.route('/ui/tree', methods=['GET'])
@login_required
def get_ui_tree():
    """Get permission tree for UI rendering"""
    try:
        tree = build_permission_tree()
        return jsonify({
            'success': True,
            'data': tree
        })
    except Exception as e:
        logger.error(f"Error getting UI tree: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@permissions_api.route('/ui/user/<int:user_id>/tree', methods=['GET'])
@login_required
@check_permission(module='usuarios', function='permissoes')
def get_user_ui_tree(user_id):
    """Get user-specific permission tree for UI"""
    try:
        tree = get_user_permissions_tree(user_id)
        return jsonify({
            'success': True,
            'data': tree
        })
    except Exception as e:
        logger.error(f"Error getting user UI tree: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500