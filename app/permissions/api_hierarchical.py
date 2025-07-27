"""
Hierarchical Permission Management API
=====================================

Additional API endpoints for the hierarchical permission management interface.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.permissions.models import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate, BatchPermissionOperation,
    UsuarioVendedor, UsuarioEquipeVendas, LogPermissao
)
from app.permissions.decorators import require_permission
from app.permissions.cache import invalidate_user_permissions
from app.auth.models import Usuario
from app.utils.timezone import agora_brasil
from datetime import timedelta
import json
import logging

logger = logging.getLogger(__name__)

# Create blueprint  
hierarchical_api = Blueprint('hierarchical_api', __name__, url_prefix='/permissions/api')

# Helper functions
def build_hierarchical_tree(user_id=None):
    """Build complete hierarchical permission tree with user permissions if specified"""
    tree = []
    
    # Get all categories
    categories = PermissionCategory.query.filter_by(active=True).order_by(PermissionCategory.order_index).all()
    
    # Get user permissions if user_id provided
    user_perms = {}
    if user_id:
        permissions = UserPermission.query.filter_by(
            user_id=user_id,
            active=True
        ).all()
        
        for perm in permissions:
            key = f"{perm.entity_type}_{perm.entity_id}"
            user_perms[key] = {
                'can_view': perm.can_view,
                'can_edit': perm.can_edit,
                'can_delete': perm.can_delete,
                'can_export': perm.can_export,
                'custom_override': perm.custom_override,
                'expires_at': perm.expires_at.isoformat() if perm.expires_at else None
            }
    
    for category in categories:
        category_data = {
            'id': category.id,
            'name': category.name,
            'display_name': category.display_name,
            'description': category.description,
            'icon': category.icon,
            'color': category.color,
            'modules': []
        }
        
        # Add user permissions if available
        if user_id:
            category_data['permissions'] = user_perms.get(f"CATEGORY_{category.id}", {
                'can_view': False,
                'can_edit': False
            })
        
        # Get modules
        modules = category.modules.filter_by(active=True).order_by(PermissionModule.order_index).all()
        
        for module in modules:
            module_data = {
                'id': module.id,
                'name': module.name,
                'display_name': module.display_name,
                'description': module.description,
                'icon': module.icon,
                'color': module.color,
                'submodules': []
            }
            
            # Add user permissions if available
            if user_id:
                module_data['permissions'] = user_perms.get(f"MODULE_{module.id}", {
                    'can_view': False,
                    'can_edit': False
                })
            
            # Get submodules
            submodules = module.submodules.filter_by(active=True).order_by(PermissionSubModule.order_index).all()
            
            for submodule in submodules:
                submodule_data = {
                    'id': submodule.id,
                    'name': submodule.name,
                    'display_name': submodule.display_name,
                    'description': submodule.description,
                    'route_pattern': submodule.route_pattern,
                    'critical_level': submodule.critical_level
                }
                
                # Add user permissions if available
                if user_id:
                    submodule_data['permissions'] = user_perms.get(f"SUBMODULE_{submodule.id}", {
                        'can_view': False,
                        'can_edit': False
                    })
                
                module_data['submodules'].append(submodule_data)
            
            category_data['modules'].append(module_data)
        
        tree.append(category_data)
    
    return tree

# API Endpoints

@hierarchical_api.route('/hierarchy/<int:user_id>')
@login_required
@require_permission('usuarios.permissoes')
def get_user_hierarchy(user_id):
    """Get hierarchical permission tree for a specific user"""
    try:
        # Check if user exists
        user = Usuario.query.get_or_404(user_id)
        
        # Build hierarchy with user permissions
        hierarchy = build_hierarchical_tree(user_id)
        
        # Get user info
        user_info = {
            'id': user.id,
            'name': user.nome,
            'email': user.email,
            'profile': user.perfil,
            'vendor_count': UsuarioVendedor.query.filter_by(
                usuario_id=user_id,
                ativo=True
            ).count(),
            'team_count': UsuarioEquipeVendas.query.filter_by(
                usuario_id=user_id,
                ativo=True
            ).count(),
            'permission_count': UserPermission.query.filter_by(
                user_id=user_id,
                active=True,
                can_view=True
            ).count()
        }
        
        return jsonify({
            'success': True,
            'user': user_info,
            'hierarchy': hierarchy
        })
        
    except Exception as e:
        logger.error(f"Error getting user hierarchy: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar hierarquia de permissões'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/permissions/batch', methods=['POST'])
@login_required
@require_permission('usuarios.permissoes')
def update_permissions_batch(user_id):
    """Update user permissions in batch with hierarchical logic"""
    try:
        data = request.get_json()
        permissions = data.get('permissions', {})
        reason = data.get('reason', 'Atualização de permissões')
        
        # Start batch operation
        batch_op = BatchPermissionOperation(
            operation_type='UPDATE',
            description=f'Batch permission update for user {user_id}',
            executed_by=current_user.id,
            status='IN_PROGRESS'
        )
        db.session.add(batch_op)
        db.session.flush()
        
        affected_count = 0
        
        # Process categories
        for cat_perm in permissions.get('categories', []):
            perm = UserPermission.query.filter_by(
                user_id=user_id,
                entity_type='CATEGORY',
                entity_id=cat_perm['id']
            ).first()
            
            if not perm:
                perm = UserPermission(
                    user_id=user_id,
                    entity_type='CATEGORY',
                    entity_id=cat_perm['id'],
                    granted_by=current_user.id
                )
                db.session.add(perm)
            
            perm.can_view = cat_perm.get('can_view', False)
            perm.can_edit = cat_perm.get('can_edit', False)
            perm.can_delete = cat_perm.get('can_delete', False)
            perm.can_export = cat_perm.get('can_export', False)
            perm.active = True
            perm.reason = reason
            
            affected_count += 1
        
        # Process modules
        for mod_perm in permissions.get('modules', []):
            perm = UserPermission.query.filter_by(
                user_id=user_id,
                entity_type='MODULE',
                entity_id=mod_perm['id']
            ).first()
            
            if not perm:
                perm = UserPermission(
                    user_id=user_id,
                    entity_type='MODULE',
                    entity_id=mod_perm['id'],
                    granted_by=current_user.id
                )
                db.session.add(perm)
            
            perm.can_view = mod_perm.get('can_view', False)
            perm.can_edit = mod_perm.get('can_edit', False)
            perm.can_delete = mod_perm.get('can_delete', False)
            perm.can_export = mod_perm.get('can_export', False)
            perm.active = True
            perm.reason = reason
            
            affected_count += 1
        
        # Process submodules
        for sub_perm in permissions.get('submodules', []):
            perm = UserPermission.query.filter_by(
                user_id=user_id,
                entity_type='SUBMODULE',
                entity_id=sub_perm['id']
            ).first()
            
            if not perm:
                perm = UserPermission(
                    user_id=user_id,
                    entity_type='SUBMODULE',
                    entity_id=sub_perm['id'],
                    granted_by=current_user.id
                )
                db.session.add(perm)
            
            perm.can_view = sub_perm.get('can_view', False)
            perm.can_edit = sub_perm.get('can_edit', False)
            perm.can_delete = sub_perm.get('can_delete', False)
            perm.can_export = sub_perm.get('can_export', False)
            perm.active = True
            perm.reason = reason
            
            affected_count += 1
        
        # Update batch operation
        batch_op.affected_permissions = affected_count
        batch_op.status = 'COMPLETED'
        batch_op.completed_at = agora_brasil()
        
        db.session.commit()
        
        # Invalidate cache
        invalidate_user_permissions(user_id)
        
        # Log action
        LogPermissao.registrar(
            usuario_id=user_id,
            acao='PERMISSOES_BATCH_UPDATE',
            detalhes=json.dumps({
                'updated_by': current_user.id,
                'affected_count': affected_count,
                'reason': reason
            }),
            resultado='SUCESSO',
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': f'{affected_count} permissões atualizadas com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Error updating permissions batch: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao atualizar permissões'
        }), 500

@hierarchical_api.route('/templates')
@login_required
@require_permission('usuarios.permissoes')
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
                'is_system': template.is_system
            })
        
        return jsonify({
            'success': True,
            'templates': template_list
        })
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao listar templates'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/permissions/template', methods=['POST'])
@login_required
@require_permission('usuarios.permissoes')
def apply_template(user_id):
    """Apply a permission template to a user"""
    try:
        data = request.get_json()
        template_id = data.get('template_id')
        
        if not template_id:
            return jsonify({
                'success': False,
                'message': 'Template ID é obrigatório'
            }), 400
        
        # Get template
        template = PermissionTemplate.query.get_or_404(template_id)
        
        # Parse template permissions
        template_perms = template.get_permissions()
        
        # Start batch operation
        batch_op = BatchPermissionOperation(
            operation_type='TEMPLATE',
            description=f'Apply template {template.name} to user {user_id}',
            executed_by=current_user.id,
            status='IN_PROGRESS'
        )
        db.session.add(batch_op)
        db.session.flush()
        
        affected_count = 0
        
        # Apply template permissions
        for entity_type, entities in template_perms.items():
            for entity_id, perms in entities.items():
                # Find or create permission
                perm = UserPermission.query.filter_by(
                    user_id=user_id,
                    entity_type=entity_type.upper(),
                    entity_id=int(entity_id)
                ).first()
                
                if not perm:
                    perm = UserPermission(
                        user_id=user_id,
                        entity_type=entity_type.upper(),
                        entity_id=int(entity_id),
                        granted_by=current_user.id
                    )
                    db.session.add(perm)
                
                perm.can_view = perms.get('can_view', False)
                perm.can_edit = perms.get('can_edit', False)
                perm.can_delete = perms.get('can_delete', False)
                perm.can_export = perms.get('can_export', False)
                perm.active = True
                perm.reason = f'Template: {template.name}'
                
                affected_count += 1
        
        # Update batch operation
        batch_op.affected_permissions = affected_count
        batch_op.status = 'COMPLETED'
        batch_op.completed_at = agora_brasil()
        
        db.session.commit()
        
        # Invalidate cache
        invalidate_user_permissions(user_id)
        
        # Log action
        LogPermissao.registrar(
            usuario_id=user_id,
            acao='TEMPLATE_APLICADO',
            detalhes=json.dumps({
                'template_id': template_id,
                'template_name': template.name,
                'applied_by': current_user.id,
                'affected_count': affected_count
            }),
            resultado='SUCESSO',
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': f'Template aplicado com sucesso. {affected_count} permissões configuradas.'
        })
        
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao aplicar template'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/vendors')
@login_required
def get_user_vendors(user_id):
    """Get user's associated vendors"""
    try:
        vendors = UsuarioVendedor.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()
        
        vendor_list = []
        for vendor in vendors:
            vendor_list.append({
                'id': vendor.id,
                'name': vendor.vendedor,
                'added_at': vendor.adicionado_em.isoformat() if vendor.adicionado_em else None,
                'added_by': vendor.adicionado_por
            })
        
        return jsonify({
            'success': True,
            'vendors': vendor_list
        })
        
    except Exception as e:
        logger.error(f"Error getting user vendors: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar vendedores'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/vendors/available')
@login_required
@require_permission('usuarios.permissoes')
def get_available_vendors(user_id):
    """Get vendors available to assign to user"""
    try:
        # Get current vendors
        current_vendors = [v.vendedor for v in UsuarioVendedor.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()]
        
        # Get all available vendors from faturamento data
        from app.faturamento.models import RelatorioFaturamentoImportado
        all_vendors = db.session.query(
            RelatorioFaturamentoImportado.vendedor
        ).filter(
            RelatorioFaturamentoImportado.vendedor.isnot(None)
        ).distinct().all()
        
        available_vendors = [
            v[0] for v in all_vendors 
            if v[0] and v[0] not in current_vendors
        ]
        
        return jsonify({
            'success': True,
            'available_vendors': sorted(available_vendors)
        })
        
    except Exception as e:
        logger.error(f"Error getting available vendors: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar vendedores disponíveis'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/vendors', methods=['POST'])
@login_required
@require_permission('usuarios.permissoes')
def add_vendor(user_id):
    """Add vendor to user"""
    try:
        data = request.get_json()
        vendor = data.get('vendor')
        observations = data.get('observations', '')
        
        if not vendor:
            return jsonify({
                'success': False,
                'message': 'Vendedor é obrigatório'
            }), 400
        
        # Check if already exists
        existing = UsuarioVendedor.query.filter_by(
            usuario_id=user_id,
            vendedor=vendor
        ).first()
        
        if existing:
            if existing.ativo:
                return jsonify({
                    'success': False,
                    'message': 'Vendedor já está associado'
                }), 409
            else:
                # Reactivate
                existing.ativo = True
                existing.adicionado_por = current_user.id
                existing.observacoes = observations
        else:
            # Create new
            new_vendor = UsuarioVendedor(
                usuario_id=user_id,
                vendedor=vendor,
                adicionado_por=current_user.id,
                observacoes=observations
            )
            db.session.add(new_vendor)
        
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=user_id,
            acao='VENDEDOR_ADICIONADO',
            detalhes=f"Vendedor: {vendor}",
            resultado='SUCESSO',
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Vendedor adicionado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Error adding vendor: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao adicionar vendedor'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/vendors/<int:vendor_id>', methods=['DELETE'])
@login_required
@require_permission('usuarios.permissoes')
def remove_vendor(user_id, vendor_id):
    """Remove vendor from user"""
    try:
        vendor = UsuarioVendedor.query.filter_by(
            id=vendor_id,
            usuario_id=user_id
        ).first()
        
        if not vendor:
            return jsonify({
                'success': False,
                'message': 'Vendedor não encontrado'
            }), 404
        
        # Soft delete
        vendor.ativo = False
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=user_id,
            acao='VENDEDOR_REMOVIDO',
            detalhes=f"Vendedor: {vendor.vendedor}",
            resultado='SUCESSO',
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Vendedor removido com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Error removing vendor: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao remover vendedor'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/teams')
@login_required
def get_user_teams(user_id):
    """Get user's associated teams"""
    try:
        teams = UsuarioEquipeVendas.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()
        
        team_list = []
        for team in teams:
            team_list.append({
                'id': team.id,
                'name': team.equipe_vendas,
                'added_at': team.adicionado_em.isoformat() if team.adicionado_em else None,
                'added_by': team.adicionado_por
            })
        
        return jsonify({
            'success': True,
            'teams': team_list
        })
        
    except Exception as e:
        logger.error(f"Error getting user teams: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar equipes'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/teams/available')
@login_required
@require_permission('usuarios.permissoes')
def get_available_teams(user_id):
    """Get teams available to assign to user"""
    try:
        # Get current teams
        current_teams = [t.equipe_vendas for t in UsuarioEquipeVendas.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()]
        
        # Get all available teams from faturamento data
        from app.faturamento.models import RelatorioFaturamentoImportado
        all_teams = db.session.query(
            RelatorioFaturamentoImportado.equipe_vendas
        ).filter(
            RelatorioFaturamentoImportado.equipe_vendas.isnot(None)
        ).distinct().all()
        
        available_teams = [
            t[0] for t in all_teams 
            if t[0] and t[0] not in current_teams
        ]
        
        return jsonify({
            'success': True,
            'available_teams': sorted(available_teams)
        })
        
    except Exception as e:
        logger.error(f"Error getting available teams: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar equipes disponíveis'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/teams', methods=['POST'])
@login_required
@require_permission('usuarios.permissoes')
def add_team(user_id):
    """Add team to user"""
    try:
        data = request.get_json()
        team = data.get('team')
        observations = data.get('observations', '')
        
        if not team:
            return jsonify({
                'success': False,
                'message': 'Equipe é obrigatória'
            }), 400
        
        # Check if already exists
        existing = UsuarioEquipeVendas.query.filter_by(
            usuario_id=user_id,
            equipe_vendas=team
        ).first()
        
        if existing:
            if existing.ativo:
                return jsonify({
                    'success': False,
                    'message': 'Equipe já está associada'
                }), 409
            else:
                # Reactivate
                existing.ativo = True
                existing.adicionado_por = current_user.id
                existing.observacoes = observations
        else:
            # Create new
            new_team = UsuarioEquipeVendas(
                usuario_id=user_id,
                equipe_vendas=team,
                adicionado_por=current_user.id,
                observacoes=observations
            )
            db.session.add(new_team)
        
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=user_id,
            acao='EQUIPE_ADICIONADA',
            detalhes=f"Equipe: {team}",
            resultado='SUCESSO',
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Equipe adicionada com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Error adding team: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao adicionar equipe'
        }), 500

@hierarchical_api.route('/users/<int:user_id>/teams/<int:team_id>', methods=['DELETE'])
@login_required
@require_permission('usuarios.permissoes')
def remove_team(user_id, team_id):
    """Remove team from user"""
    try:
        team = UsuarioEquipeVendas.query.filter_by(
            id=team_id,
            usuario_id=user_id
        ).first()
        
        if not team:
            return jsonify({
                'success': False,
                'message': 'Equipe não encontrada'
            }), 404
        
        # Soft delete
        team.ativo = False
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=user_id,
            acao='EQUIPE_REMOVIDA',
            detalhes=f"Equipe: {team.equipe_vendas}",
            resultado='SUCESSO',
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Equipe removida com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Error removing team: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao remover equipe'
        }), 500