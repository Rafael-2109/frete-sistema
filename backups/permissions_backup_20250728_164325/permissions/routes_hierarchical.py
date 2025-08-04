"""
Hierarchical Permission Management Routes
=========================================

Routes for the new hierarchical permission management interface.
"""

from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app.permissions.decorators_simple import require_permission
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    UsuarioVendedor, UsuarioEquipeVendas, Vendedor, EquipeVendas,
    PermissionCategory
)
from app.permissions.vendor_team_manager import VendorTeamManager
from app.permissions.module_scanner import ModuleScanner
from app.auth.models import Usuario
from app import db
import logging
import json

logger = logging.getLogger(__name__)

# Import blueprint from __init__.py to avoid duplication
from . import permissions_bp

@permissions_bp.route('/hierarchical-manager')
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def hierarchical_manager():
    """Main hierarchical permission management interface"""
    try:
        # Get statistics
        stats = {
            'total_usuarios': Usuario.query.filter_by(status='ativo').count(),
            'total_vendedores': Vendedor.query.filter_by(ativo=True).count(),
            'total_equipes': EquipeVendas.query.filter_by(ativo=True).count(),
            'total_permissoes': PermissaoUsuario.query.filter_by(ativo=True).count(),
        }
        
        return render_template('permissions/hierarchical_manager.html', stats=stats)
    except Exception as e:
        logger.error(f"Error loading hierarchical manager: {e}")
        return render_template('permissions/hierarchical_manager.html', stats={})

@permissions_bp.route('/api/hierarchical/users')
@login_required
@require_permission('permissions', 'gerenciar', 'visualizar')
def api_get_hierarchical_users():
    """Get all users for the hierarchical interface"""
    try:
        # Debug: check if table exists and has data
        logger.info("Fetching users from database...")
        
        users = Usuario.query.filter_by(status='ativo').order_by(Usuario.nome).all()
        logger.info(f"Found {len(users)} active users")
        
        users_data = []
        for user in users:
            # Get vendor and team counts (handle if tables don't exist)
            try:
                vendor_count = UsuarioVendedor.query.filter_by(
                    usuario_id=user.id, 
                    ativo=True
                ).count()
            except:
                vendor_count = 0
            
            try:
                team_count = UsuarioEquipeVendas.query.filter_by(
                    usuario_id=user.id,
                    ativo=True
                ).count()
            except:
                team_count = 0
            
            users_data.append({
                'id': user.id,
                'nome': user.nome,
                'email': user.email,
                'perfil': user.perfil_nome or user.perfil,
                'vendedor_count': vendor_count,
                'equipe_count': team_count,
                'ativo': user.status == 'ativo'
            })
        
        return jsonify({'success': True, 'users': users_data})
    except Exception as e:
        logger.error(f"Error getting hierarchical users: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/permissions/<int:user_id>')
@login_required
@require_permission('permissions', 'gerenciar', 'visualizar')
def api_get_hierarchical_permissions(user_id):
    """Get hierarchical permissions for a specific user"""
    try:
        # Get user
        user = Usuario.query.get_or_404(user_id)
        
        # Get all categories with modules
        categories = PermissionCategory.query.filter_by(ativo=True).order_by(PermissionCategory.ordem).all()
        
        hierarchy = []
        
        for category in categories:
            # Get modules in this category
            modules = ModuloSistema.query.filter_by(
                category_id=category.id,
                ativo=True
            ).order_by(ModuloSistema.ordem).all()
            
            category_data = {
                'id': f'cat_{category.id}',
                'nome': category.nome_exibicao,
                'tipo': 'category',
                'pode_visualizar': False,
                'pode_editar': False,
                'modulos': []
            }
            
            for module in modules:
                # Get user permission for this module
                permission = PermissaoUsuario.query.filter_by(
                    usuario_id=user_id,
                    funcao_id=module.id,
                    ativo=True
                ).first()
                
                # Get inherited permissions from vendor/team
                inherited = VendorTeamManager.verificar_permissao(
                    usuario_id=user_id,
                    funcao_id=module.id
                )
                
                module_data = {
                    'id': f'mod_{module.id}',
                    'nome': module.nome_exibicao,
                    'tipo': 'module',
                    'pode_visualizar': permission.pode_visualizar if permission else inherited['visualizar'],
                    'pode_editar': permission.pode_editar if permission else inherited['editar'],
                    'herdado': not bool(permission),
                    'funcoes': []
                }
                
                # Get functions in this module
                functions = FuncaoModulo.query.filter_by(
                    modulo_id=module.id,
                    ativo=True
                ).order_by(FuncaoModulo.ordem).all()
                
                for function in functions:
                    # Get user permission for this function
                    func_permission = PermissaoUsuario.query.filter_by(
                        usuario_id=user_id,
                        funcao_id=function.id,
                        ativo=True
                    ).first()
                    
                    func_data = {
                        'id': f'func_{function.id}',
                        'nome': function.nome_exibicao,
                        'tipo': 'function',
                        'pode_visualizar': func_permission.pode_visualizar if func_permission else module_data['pode_visualizar'],
                        'pode_editar': func_permission.pode_editar if func_permission else module_data['pode_editar'],
                        'herdado': not bool(func_permission)
                    }
                    
                    module_data['funcoes'].append(func_data)
                
                # Update category permissions based on modules
                if module_data['pode_visualizar']:
                    category_data['pode_visualizar'] = True
                if module_data['pode_editar']:
                    category_data['pode_editar'] = True
                
                category_data['modulos'].append(module_data)
            
            hierarchy.append(category_data)
        
        # Get vendor and team associations
        vendors = []
        vendor_assocs = UsuarioVendedor.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()
        
        for assoc in vendor_assocs:
            vendor = Vendedor.query.get(assoc.vendedor_id)
            if vendor:
                vendors.append({
                    'id': vendor.id,
                    'codigo': vendor.codigo,
                    'nome': vendor.nome,
                    'tipo_acesso': assoc.tipo_acesso
                })
        
        teams = []
        team_assocs = UsuarioEquipeVendas.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()
        
        for assoc in team_assocs:
            team = EquipeVendas.query.get(assoc.equipe_id)
            if team:
                teams.append({
                    'id': team.id,
                    'codigo': team.codigo,
                    'nome': team.nome,
                    'cargo': assoc.cargo_equipe,
                    'tipo_acesso': assoc.tipo_acesso
                })
        
        return jsonify({
            'success': True,
            'permissions': hierarchy,
            'vendors': vendors,
            'teams': teams,
            'user': {
                'id': user.id,
                'nome': user.nome,
                'email': user.email,
                'perfil': user.perfil_nome or user.perfil
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting hierarchical permissions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/permissions/batch', methods=['POST'])
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def api_update_hierarchical_permissions_batch():
    """Update permissions in batch for hierarchical interface"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        permissions = data.get('permissions', [])
        
        if not user_id:
            return jsonify({'success': False, 'error': 'ID do usuário é obrigatório'}), 400
        
        # Verify user exists
        user = Usuario.query.get_or_404(user_id)
        
        # Process each permission update
        for perm_data in permissions:
            perm_id = perm_data.get('id', '')
            pode_visualizar = perm_data.get('pode_visualizar', False)
            pode_editar = perm_data.get('pode_editar', False)
            
            # Extract type and ID
            parts = perm_id.split('_')
            if len(parts) != 2:
                continue
                
            perm_type, entity_id = parts[0], int(parts[1])
            
            if perm_type == 'mod':
                # Update module permission
                module = ModuloSistema.query.get(entity_id)
                if module:
                    # Find or create permission
                    permission = PermissaoUsuario.query.filter_by(
                        usuario_id=user_id,
                        funcao_id=module.id
                    ).first()
                    
                    if permission:
                        permission.pode_visualizar = pode_visualizar
                        permission.pode_editar = pode_editar
                        permission.ativo = True
                    else:
                        permission = PermissaoUsuario(
                            usuario_id=user_id,
                            funcao_id=module.id,
                            pode_visualizar=pode_visualizar,
                            pode_editar=pode_editar,
                            ativo=True
                        )
                        db.session.add(permission)
            
            elif perm_type == 'func':
                # Update function permission
                function = FuncaoModulo.query.get(entity_id)
                if function:
                    # Find or create permission
                    permission = PermissaoUsuario.query.filter_by(
                        usuario_id=user_id,
                        funcao_id=function.id
                    ).first()
                    
                    if permission:
                        permission.pode_visualizar = pode_visualizar
                        permission.pode_editar = pode_editar
                        permission.ativo = True
                    else:
                        permission = PermissaoUsuario(
                            usuario_id=user_id,
                            funcao_id=function.id,
                            pode_visualizar=pode_visualizar,
                            pode_editar=pode_editar,
                            ativo=True
                        )
                        db.session.add(permission)
        
        db.session.commit()
        
        # Log the action
        logger.info(f"Batch permission update for user {user_id} by {current_user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Permissões atualizadas com sucesso!'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating hierarchical permissions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/vendors')
@login_required
@require_permission('permissions', 'gerenciar', 'visualizar')
def api_get_vendors():
    """Get all active vendors"""
    try:
        vendors = Vendedor.query.filter_by(ativo=True).order_by(Vendedor.nome).all()
        
        vendors_data = []
        for vendor in vendors:
            vendors_data.append({
                'id': vendor.id,
                'codigo': vendor.codigo,
                'nome': vendor.nome,
                'razao_social': vendor.razao_social,
                'cnpj': vendor.cnpj
            })
        
        return jsonify({'success': True, 'vendors': vendors_data})
    except Exception as e:
        logger.error(f"Error getting vendors: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/teams')
@login_required
@require_permission('permissions', 'gerenciar', 'visualizar')
def api_get_teams():
    """Get all active sales teams"""
    try:
        teams = EquipeVendas.query.filter_by(ativo=True).order_by(EquipeVendas.nome).all()
        
        teams_data = []
        for team in teams:
            teams_data.append({
                'id': team.id,
                'codigo': team.codigo,
                'nome': team.nome,
                'descricao': team.descricao,
                'gerente': team.gerente
            })
        
        return jsonify({'success': True, 'teams': teams_data})
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/user/<int:user_id>/vendors', methods=['POST'])
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def api_associate_user_vendor(user_id):
    """Associate user with vendor"""
    try:
        data = request.get_json()
        vendor_id = data.get('vendor_id')
        tipo_acesso = data.get('tipo_acesso', 'visualizar')
        
        result = VendorTeamManager.associar_usuario_vendedor(
            usuario_id=user_id,
            vendedor_id=vendor_id,
            tipo_acesso=tipo_acesso
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Vendedor associado com sucesso!'})
        else:
            return jsonify({'success': False, 'error': 'Erro ao associar vendedor'}), 400
            
    except Exception as e:
        logger.error(f"Error associating vendor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/user/<int:user_id>/vendors/<int:vendor_id>', methods=['DELETE'])
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def api_disassociate_user_vendor(user_id, vendor_id):
    """Disassociate user from vendor"""
    try:
        result = VendorTeamManager.desassociar_usuario_vendedor(
            usuario_id=user_id,
            vendedor_id=vendor_id
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Vendedor desassociado com sucesso!'})
        else:
            return jsonify({'success': False, 'error': 'Erro ao desassociar vendedor'}), 400
            
    except Exception as e:
        logger.error(f"Error disassociating vendor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/user/<int:user_id>/teams', methods=['POST'])
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def api_associate_user_team(user_id):
    """Associate user with team"""
    try:
        data = request.get_json()
        team_id = data.get('team_id')
        cargo = data.get('cargo', 'Membro')
        tipo_acesso = data.get('tipo_acesso', 'membro')
        
        result = VendorTeamManager.associar_usuario_equipe(
            usuario_id=user_id,
            equipe_id=team_id,
            cargo_equipe=cargo,
            tipo_acesso=tipo_acesso
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Equipe associada com sucesso!'})
        else:
            return jsonify({'success': False, 'error': 'Erro ao associar equipe'}), 400
            
    except Exception as e:
        logger.error(f"Error associating team: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/user/<int:user_id>/teams/<int:team_id>', methods=['DELETE'])
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def api_disassociate_user_team(user_id, team_id):
    """Disassociate user from team"""
    try:
        result = VendorTeamManager.desassociar_usuario_equipe(
            usuario_id=user_id,
            equipe_id=team_id
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Equipe desassociada com sucesso!'})
        else:
            return jsonify({'success': False, 'error': 'Erro ao desassociar equipe'}), 400
            
    except Exception as e:
        logger.error(f"Error disassociating team: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/templates')
@login_required
@require_permission('permissions', 'gerenciar', 'visualizar')
def api_get_permission_templates():
    """Get available permission templates"""
    try:
        # For now, return hardcoded templates
        # TODO: Create PermissionTemplate model
        templates = [
            {
                'id': 1,
                'nome': 'Vendedor Básico',
                'descricao': 'Acesso básico para vendedores',
                'permissions': {
                    'faturamento': {'view': True, 'edit': False},
                    'carteira': {'view': True, 'edit': False},
                    'monitoramento': {'view': True, 'edit': False}
                }
            },
            {
                'id': 2,
                'nome': 'Supervisor',
                'descricao': 'Acesso de supervisor com edição',
                'permissions': {
                    'faturamento': {'view': True, 'edit': True},
                    'carteira': {'view': True, 'edit': True},
                    'monitoramento': {'view': True, 'edit': True},
                    'embarques': {'view': True, 'edit': False}
                }
            },
            {
                'id': 3,
                'nome': 'Gerente',
                'descricao': 'Acesso completo de gerência',
                'permissions': {
                    'faturamento': {'view': True, 'edit': True},
                    'carteira': {'view': True, 'edit': True},
                    'monitoramento': {'view': True, 'edit': True},
                    'embarques': {'view': True, 'edit': True},
                    'financeiro': {'view': True, 'edit': True},
                    'usuarios': {'view': True, 'edit': False}
                }
            }
        ]
        
        return jsonify({'success': True, 'templates': templates})
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/scan-modules')
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def api_scan_modules():
    """Scan application for modules and functions"""
    try:
        modules = ModuleScanner.scan_application()
        return jsonify({
            'success': True, 
            'modules': modules,
            'count': len(modules)
        })
    except Exception as e:
        logger.error(f"Error scanning modules: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@permissions_bp.route('/api/hierarchical/initialize-from-scan', methods=['POST'])
@login_required
@require_permission('permissions', 'gerenciar', 'editar')
def api_initialize_from_scan():
    """Initialize permission structure from scan"""
    try:
        success = ModuleScanner.initialize_permissions_from_scan()
        if success:
            return jsonify({
                'success': True,
                'message': 'Estrutura de permissões inicializada com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao inicializar estrutura de permissões'
            }), 500
    except Exception as e:
        logger.error(f"Error initializing from scan: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500