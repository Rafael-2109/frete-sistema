"""
Permission System Routes
=======================

Flask routes for the permission management UI and additional API endpoints.
"""

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.permissions.decorators import require_permission
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, FuncaoModulo, PermissaoUsuario,
    UsuarioVendedor, UsuarioEquipeVendas, LogPermissao,
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate
)
from app.auth.models import Usuario
from app import db
import logging

logger = logging.getLogger(__name__)

# Import blueprint from __init__.py to avoid duplication
from . import permissions_bp

# ============================================================================
# UI ROUTES
# ============================================================================

@permissions_bp.route('/')
@login_required
def index():
    """Main permission page - redirects to appropriate view"""
    if current_user.perfil_nome == 'admin':
        return admin_index()
    else:
        # Regular users see their own permissions
        return render_template('permissions/user_permissions.html', 
                             usuario=current_user)

@permissions_bp.route('/admin')
@login_required
@require_permission('admin.permissions')
def admin_index():
    """Main permission administration page (legacy)"""
    try:
        # Get statistics
        stats = {
            'total_usuarios': Usuario.query.filter_by(status='ativo').count(),
            'total_permissoes': PermissaoUsuario.query.filter_by(ativo=True).count(),
            'total_modulos': ModuloSistema.query.filter_by(ativo=True).count(),
            'total_funcoes': FuncaoModulo.query.filter_by(ativo=True).count()
        }
        
        # Get users and profiles
        usuarios = Usuario.query.filter_by(status='ativo').order_by(Usuario.nome).all()
        perfis = PerfilUsuario.query.filter_by(ativo=True).order_by(PerfilUsuario.nome).all()
        
        return render_template('permissions/admin_index.html',
                             stats=stats,
                             usuarios=usuarios,
                             perfis=perfis)
    except Exception as e:
        logger.error(f"Error loading admin index: {e}")
        return render_template('error.html', error="Erro ao carregar página de permissões"), 500

@permissions_bp.route('/hierarchical')
@login_required
@require_permission('admin.permissions')
def hierarchical_admin():
    """New hierarchical permission management interface"""
    try:
        return render_template('permissions/hierarchical_admin.html')
    except Exception as e:
        logger.error(f"Error loading hierarchical admin: {e}")
        return render_template('error.html', error="Erro ao carregar interface de permissões"), 500


# ============================================================================
# API ROUTES (Additional to permissions.api)
# ============================================================================

@permissions_bp.route('/api/users', methods=['GET'])
@login_required
@require_permission('usuarios.listar')
def api_list_users():
    """List all active users for the permission manager"""
    try:
        users = Usuario.query.filter_by(status='ativo').order_by(Usuario.nome).all()
        
        users_data = []
        for user in users:
            # Count permissions
            permission_count = UserPermission.query.filter_by(
                user_id=user.id,
                active=True
            ).count()
            
            users_data.append({
                'id': user.id,
                'nome': user.nome,
                'email': user.email,
                'perfil': user.perfil,
                'permission_count': permission_count,
                'vendor_count': UsuarioVendedor.query.filter_by(
                    usuario_id=user.id,
                    ativo=True
                ).count(),
                'team_count': UsuarioEquipeVendas.query.filter_by(
                    usuario_id=user.id,
                    ativo=True
                ).count()
            })
        
        return jsonify({
            'success': True,
            'users': users_data,
            'total': len(users_data)
        })
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao listar usuários'
        }), 500

@permissions_bp.route('/api/usuario/<int:usuario_id>/permissoes', methods=['GET'])
@login_required
def api_get_user_permissions_legacy(usuario_id):
    """Legacy endpoint for getting user permissions"""
    try:
        # Check authorization
        if not (current_user.is_admin or current_user.id == usuario_id):
            return jsonify({
                'success': False,
                'message': 'Acesso negado'
            }), 403
        
        usuario = Usuario.query.get_or_404(usuario_id)
        
        # Get vendors
        vendedores = UsuarioVendedor.query.filter_by(
            usuario_id=usuario_id,
            ativo=True
        ).all()
        
        vendedores_data = [{
            'id': v.id,
            'vendedor': v.vendedor,
            'adicionado_em': v.adicionado_em.isoformat() if v.adicionado_em else None
        } for v in vendedores]
        
        # Get teams
        equipes = UsuarioEquipeVendas.query.filter_by(
            usuario_id=usuario_id,
            ativo=True
        ).all()
        
        equipes_data = [{
            'id': e.id,
            'equipe_vendas': e.equipe_vendas,
            'adicionado_em': e.adicionado_em.isoformat() if e.adicionado_em else None
        } for e in equipes]
        
        # Get modules and permissions (legacy format)
        modulos = ModuloSistema.query.filter_by(ativo=True).order_by(ModuloSistema.ordem).all()
        modulos_data = []
        
        for modulo in modulos:
            funcoes_data = []
            for funcao in modulo.funcoes.filter_by(ativo=True).order_by(FuncaoModulo.ordem):
                permissao = PermissaoUsuario.query.filter_by(
                    usuario_id=usuario_id,
                    funcao_id=funcao.id,
                    ativo=True
                ).first()
                
                funcoes_data.append({
                    'id': funcao.id,
                    'nome': funcao.nome,
                    'nome_exibicao': funcao.nome_exibicao,
                    'nivel_critico': funcao.nivel_critico.lower() if funcao.nivel_critico else 'normal',
                    'permissao': {
                        'id': permissao.id if permissao else None,
                        'pode_visualizar': permissao.pode_visualizar if permissao else False,
                        'pode_editar': permissao.pode_editar if permissao else False
                    }
                })
            
            modulos_data.append({
                'id': modulo.id,
                'nome': modulo.nome,
                'nome_exibicao': modulo.nome_exibicao,
                'icone': modulo.icone,
                'cor': modulo.cor,
                'funcoes': funcoes_data
            })
        
        return jsonify({
            'success': True,
            'data': {
                'usuario': {
                    'id': usuario.id,
                    'nome': usuario.nome,
                    'email': usuario.email,
                    'perfil': usuario.perfil
                },
                'vendedores': vendedores_data,
                'equipes_vendas': equipes_data,
                'modulos': modulos_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar permissões'
        }), 500

@permissions_bp.route('/api/permissao', methods=['POST'])
@login_required
@require_permission('usuarios.permissoes')
def api_save_permission():
    """Save individual permission (legacy)"""
    try:
        data = request.get_json()
        
        usuario_id = data.get('usuario_id')
        funcao_id = data.get('funcao_id')
        pode_visualizar = data.get('pode_visualizar', False)
        pode_editar = data.get('pode_editar', False)
        
        # Validate
        if not usuario_id or not funcao_id:
            return jsonify({
                'success': False,
                'message': 'Dados inválidos'
            }), 400
        
        # Get or create permission
        permissao = PermissaoUsuario.query.filter_by(
            usuario_id=usuario_id,
            funcao_id=funcao_id
        ).first()
        
        if not permissao:
            permissao = PermissaoUsuario(
                usuario_id=usuario_id,
                funcao_id=funcao_id,
                concedida_por=current_user.id
            )
            db.session.add(permissao)
        
        # Update values
        permissao.pode_visualizar = pode_visualizar
        permissao.pode_editar = pode_editar
        permissao.ativo = True
        
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=usuario_id,
            acao='PERMISSAO_ALTERADA',
            funcao_id=funcao_id,
            detalhes=f"Visualizar: {pode_visualizar}, Editar: {pode_editar}",
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Permissão salva com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Error saving permission: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao salvar permissão'
        }), 500

@permissions_bp.route('/api/modulo/<int:modulo_id>/permissoes', methods=['POST'])
@login_required
@require_permission('usuarios.permissoes')
def api_save_module_permissions(modulo_id):
    """Save all permissions for a module (legacy)"""
    try:
        data = request.get_json()
        usuario_id = data.get('usuario_id')
        pode_visualizar = data.get('pode_visualizar', False)
        pode_editar = data.get('pode_editar', False)
        
        # Get module and its functions
        modulo = ModuloSistema.query.get_or_404(modulo_id)
        
        for funcao in modulo.funcoes.filter_by(ativo=True):
            permissao = PermissaoUsuario.query.filter_by(
                usuario_id=usuario_id,
                funcao_id=funcao.id
            ).first()
            
            if not permissao:
                permissao = PermissaoUsuario(
                    usuario_id=usuario_id,
                    funcao_id=funcao.id,
                    concedida_por=current_user.id
                )
                db.session.add(permissao)
            
            permissao.pode_visualizar = pode_visualizar
            permissao.pode_editar = pode_editar
            permissao.ativo = True
        
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=usuario_id,
            acao='MODULO_PERMISSOES_ALTERADAS',
            detalhes=f"Módulo: {modulo.nome}, Visualizar: {pode_visualizar}, Editar: {pode_editar}",
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': f'Permissões do módulo {modulo.nome_exibicao} atualizadas'
        })
        
    except Exception as e:
        logger.error(f"Error saving module permissions: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Erro ao salvar permissões do módulo'
        }), 500

@permissions_bp.route('/api/logs', methods=['GET'])
@login_required
@require_permission('admin.logs')
def api_get_logs():
    """Get permission logs"""
    try:
        usuario_id = request.args.get('usuario_id', type=int)
        limite = request.args.get('limite', 50, type=int)
        
        query = LogPermissao.query
        
        if usuario_id:
            query = query.filter_by(usuario_id=usuario_id)
        
        logs = query.order_by(LogPermissao.timestamp.desc()).limit(limite).all()
        
        logs_data = []
        for log in logs:
            log_data = {
                'id': log.id,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'acao': log.acao,
                'detalhes': log.detalhes,
                'resultado': log.resultado,
                'funcao': None
            }
            
            if log.funcao:
                log_data['funcao'] = f"{log.funcao.modulo.nome}.{log.funcao.nome}"
            
            logs_data.append(log_data)
        
        return jsonify({
            'success': True,
            'data': logs_data
        })
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar logs'
        }), 500

# Additional vendor/team endpoints for legacy support
@permissions_bp.route('/api/usuario/<int:usuario_id>/vendedores', methods=['GET'])
@login_required
def api_get_user_vendors_legacy(usuario_id):
    """Get user vendors with available options (legacy)"""
    try:
        # Get current vendors
        vendedores = UsuarioVendedor.query.filter_by(
            usuario_id=usuario_id,
            ativo=True
        ).all()
        
        vendedores_autorizados = [{
            'id': v.id,
            'vendedor': v.vendedor
        } for v in vendedores]
        
        # Get all available vendors
        from app.faturamento.models import RelatorioFaturamentoImportado
        todos_vendedores = db.session.query(
            RelatorioFaturamentoImportado.vendedor
        ).filter(
            RelatorioFaturamentoImportado.vendedor.isnot(None)
        ).distinct().all()
        
        vendedores_disponiveis = [
            v[0] for v in todos_vendedores 
            if v[0] and v[0] not in [va['vendedor'] for va in vendedores_autorizados]
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'vendedores_autorizados': vendedores_autorizados,
                'vendedores_disponiveis': sorted(vendedores_disponiveis)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting vendors: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar vendedores'
        }), 500

@permissions_bp.route('/api/usuario/<int:usuario_id>/vendedores', methods=['POST'])
@login_required
@require_permission('usuarios.permissoes')
def api_add_vendor_legacy(usuario_id):
    """Add vendor to user (legacy)"""
    try:
        data = request.get_json()
        vendedor = data.get('vendedor')
        observacoes = data.get('observacoes')
        
        if not vendedor:
            return jsonify({
                'success': False,
                'message': 'Vendedor é obrigatório'
            }), 400
        
        # Check if already exists
        existing = UsuarioVendedor.query.filter_by(
            usuario_id=usuario_id,
            vendedor=vendedor
        ).first()
        
        if existing:
            if existing.ativo:
                return jsonify({
                    'success': False,
                    'message': 'Vendedor já autorizado'
                }), 409
            else:
                # Reactivate
                existing.ativo = True
                existing.adicionado_por = current_user.id
                existing.observacoes = observacoes
        else:
            # Create new
            novo = UsuarioVendedor(
                usuario_id=usuario_id,
                vendedor=vendedor,
                adicionado_por=current_user.id,
                observacoes=observacoes
            )
            db.session.add(novo)
        
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=usuario_id,
            acao='VENDEDOR_ADICIONADO',
            detalhes=f"Vendedor: {vendedor}",
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

@permissions_bp.route('/api/usuario/<int:usuario_id>/vendedores', methods=['DELETE'])
@login_required
@require_permission('usuarios.permissoes')
def api_remove_vendor_legacy(usuario_id):
    """Remove vendor from user (legacy)"""
    try:
        vendedor_id = request.args.get('vendedor_id', type=int)
        
        if not vendedor_id:
            return jsonify({
                'success': False,
                'message': 'ID do vendedor é obrigatório'
            }), 400
        
        vendedor = UsuarioVendedor.query.filter_by(
            id=vendedor_id,
            usuario_id=usuario_id
        ).first()
        
        if not vendedor:
            return jsonify({
                'success': False,
                'message': 'Vendedor não encontrado'
            }), 404
        
        # Soft delete
        vendedor.ativo = False
        db.session.commit()
        
        # Log action
        LogPermissao.registrar(
            usuario_id=usuario_id,
            acao='VENDEDOR_REMOVIDO',
            detalhes=f"Vendedor: {vendedor.vendedor}",
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

# Similar endpoints for teams...
@permissions_bp.route('/api/usuario/<int:usuario_id>/equipes', methods=['GET'])
@login_required
def api_get_user_teams_legacy(usuario_id):
    """Get user teams with available options (legacy)"""
    try:
        # Get current teams
        equipes = UsuarioEquipeVendas.query.filter_by(
            usuario_id=usuario_id,
            ativo=True
        ).all()
        
        equipes_autorizadas = [{
            'id': e.id,
            'equipe_vendas': e.equipe_vendas
        } for e in equipes]
        
        # Get all available teams
        from app.faturamento.models import RelatorioFaturamentoImportado
        todas_equipes = db.session.query(
            RelatorioFaturamentoImportado.equipe_vendas
        ).filter(
            RelatorioFaturamentoImportado.equipe_vendas.isnot(None)
        ).distinct().all()
        
        equipes_disponiveis = [
            e[0] for e in todas_equipes 
            if e[0] and e[0] not in [ea['equipe_vendas'] for ea in equipes_autorizadas]
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'equipes_autorizadas': equipes_autorizadas,
                'equipes_disponiveis': sorted(equipes_disponiveis)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao buscar equipes'
        }), 500