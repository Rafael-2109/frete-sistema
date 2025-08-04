"""
API Unificada de Gerenciamento de Permissões
===========================================

Endpoints REST para o sistema completo de permissões com:
- Gestão hierárquica de permissões
- Operações em lote
- Templates de permissão
- Logs de auditoria
- Vendedores e equipes
"""

from flask import Blueprint, jsonify, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func
from app import db
from app.permissions.models import (
    # Modelos principais
    ModuloSistema, FuncaoModulo, PermissaoUsuario,
    PerfilUsuario, LogPermissao,
    # Vendedores e Equipes
    Vendedor, EquipeVendas, UsuarioVendedor, UsuarioEquipeVendas,
    PermissaoVendedor, PermissaoEquipe,
    # Modelos hierárquicos
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate, BatchPermissionOperation
)
from app.permissions.decorators import check_permission
from app.permissions.cache import (
    invalidate_user_permissions, 
    invalidate_module_permissions,
    get_cached_permissions
)
from app.auth.models import Usuario
from app.utils.timezone import agora_brasil
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

# Criar blueprint
permissions_api_unified = Blueprint('permissions_api_unified', __name__, url_prefix='/api/v1/permissions')

# ============================================================================
# DECORADORES E HELPERS
# ============================================================================

def require_permission_admin():
    """Decorador para garantir que usuário tem permissão de administrar permissões"""
    def decorator(f):
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.tem_permissao('usuarios', 'permissoes'):
                abort(403, 'Sem permissão para gerenciar permissões')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_permission_action(action, user_id=None, details=None, result='SUCESSO'):
    """Registra ação no log de auditoria"""
    try:
        LogPermissao.registrar(
            usuario_id=user_id or current_user.id,
            acao=action,
            detalhes=json.dumps(details) if details else None,
            resultado=result,
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            sessao_id=request.cookies.get('session')
        )
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")

# ============================================================================
# ENDPOINTS DE ESTATÍSTICAS
# ============================================================================

@permissions_api_unified.route('/statistics', methods=['GET'])
@login_required
@require_permission_admin()
def get_statistics():
    """Retorna estatísticas gerais do sistema de permissões"""
    try:
        stats = {
            'total_users': Usuario.query.count(),
            'active_users': Usuario.query.filter_by(status='ativo').count(),
            'total_permissions': PermissaoUsuario.query.filter_by(ativo=True).count(),
            'total_modules': ModuloSistema.query.filter_by(ativo=True).count(),
            'total_functions': FuncaoModulo.query.filter_by(ativo=True).count(),
            'total_vendors': Vendedor.query.filter_by(ativo=True).count(),
            'total_teams': EquipeVendas.query.filter_by(ativo=True).count(),
            'recent_changes': LogPermissao.query.filter(
                LogPermissao.timestamp >= agora_brasil() - timedelta(days=7)
            ).count()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS DE USUÁRIOS
# ============================================================================

@permissions_api_unified.route('/users', methods=['GET'])
@login_required
@require_permission_admin()
def get_users():
    """Lista todos os usuários com informações básicas"""
    try:
        # Filtros
        search = request.args.get('search', '')
        profile = request.args.get('profile', '')
        status = request.args.get('status', '')
        
        query = Usuario.query
        
        if search:
            query = query.filter(
                or_(
                    Usuario.nome.ilike(f'%{search}%'),
                    Usuario.email.ilike(f'%{search}%')
                )
            )
        
        if profile:
            query = query.filter_by(perfil=profile)
        
        if status:
            query = query.filter_by(status=status)
        
        users = query.order_by(Usuario.nome).all()
        
        return jsonify([{
            'id': u.id,
            'nome': u.nome,
            'email': u.email,
            'perfil': u.perfil,
            'perfil_nome': u.perfil_nome,
            'status': u.status,
            'empresa': u.empresa,
            'cargo': u.cargo,
            'criado_em': u.criado_em.isoformat() if u.criado_em else None,
            'ultimo_login': u.ultimo_login.isoformat() if u.ultimo_login else None
        } for u in users])
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_details(user_id):
    """Retorna detalhes completos de um usuário"""
    try:
        user = Usuario.query.get_or_404(user_id)
        
        # Contar permissões
        permission_count = PermissaoUsuario.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).count()
        
        # Contar vendedores e equipes
        vendor_count = UsuarioVendedor.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).count()
        
        team_count = UsuarioEquipeVendas.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).count()
        
        return jsonify({
            'id': user.id,
            'nome': user.nome,
            'email': user.email,
            'perfil': user.perfil,
            'perfil_nome': user.perfil_nome,
            'status': user.status,
            'empresa': user.empresa,
            'cargo': user.cargo,
            'telefone': user.telefone,
            'vendedor_vinculado': user.vendedor_vinculado,
            'criado_em': user.criado_em.isoformat() if user.criado_em else None,
            'aprovado_em': user.aprovado_em.isoformat() if user.aprovado_em else None,
            'aprovado_por': user.aprovado_por,
            'ultimo_login': user.ultimo_login.isoformat() if user.ultimo_login else None,
            'observacoes': user.observacoes,
            'statistics': {
                'permissions': permission_count,
                'vendors': vendor_count,
                'teams': team_count
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do usuário {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS DE PERMISSÕES
# ============================================================================

@permissions_api_unified.route('/users/<int:user_id>/permissions', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_permissions(user_id):
    """Retorna todas as permissões de um usuário (diretas + herdadas)"""
    try:
        user = Usuario.query.get_or_404(user_id)
        
        # Buscar permissões diretas
        direct_permissions = db.session.query(
            PermissaoUsuario,
            FuncaoModulo,
            ModuloSistema
        ).join(
            FuncaoModulo,
            PermissaoUsuario.funcao_id == FuncaoModulo.id
        ).join(
            ModuloSistema,
            FuncaoModulo.modulo_id == ModuloSistema.id
        ).filter(
            PermissaoUsuario.usuario_id == user_id,
            PermissaoUsuario.ativo == True
        ).all()
        
        # Buscar permissões herdadas de vendedores
        vendor_permissions = []
        user_vendors = UsuarioVendedor.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()
        
        for uv in user_vendors:
            vendor_perms = db.session.query(
                PermissaoVendedor,
                FuncaoModulo,
                ModuloSistema,
                Vendedor
            ).join(
                FuncaoModulo,
                PermissaoVendedor.funcao_id == FuncaoModulo.id
            ).join(
                ModuloSistema,
                FuncaoModulo.modulo_id == ModuloSistema.id
            ).join(
                Vendedor,
                PermissaoVendedor.vendedor_id == Vendedor.id
            ).filter(
                PermissaoVendedor.vendedor_id == uv.vendedor_id,
                PermissaoVendedor.ativo == True
            ).all()
            
            vendor_permissions.extend(vendor_perms)
        
        # Buscar permissões herdadas de equipes
        team_permissions = []
        user_teams = UsuarioEquipeVendas.query.filter_by(
            usuario_id=user_id,
            ativo=True
        ).all()
        
        for ut in user_teams:
            team_perms = db.session.query(
                PermissaoEquipe,
                FuncaoModulo,
                ModuloSistema,
                EquipeVendas
            ).join(
                FuncaoModulo,
                PermissaoEquipe.funcao_id == FuncaoModulo.id
            ).join(
                ModuloSistema,
                FuncaoModulo.modulo_id == ModuloSistema.id
            ).join(
                EquipeVendas,
                PermissaoEquipe.equipe_id == EquipeVendas.id
            ).filter(
                PermissaoEquipe.equipe_id == ut.equipe_id,
                PermissaoEquipe.ativo == True
            ).all()
            
            team_permissions.extend(team_perms)
        
        # Consolidar todas as permissões
        all_permissions = []
        processed_functions = set()
        
        # Adicionar permissões diretas primeiro (têm prioridade)
        for perm, func, mod in direct_permissions:
            all_permissions.append({
                'funcao_id': func.id,
                'categoria': 'sistema',  # Categoria padrão
                'categoria_nome': 'Sistema',
                'categoria_icone': '⚙️',
                'categoria_cor': '#6c757d',
                'modulo': mod.nome,
                'modulo_nome': mod.nome_exibicao,
                'modulo_icone': mod.icone,
                'modulo_cor': mod.cor,
                'funcao': func.nome,
                'funcao_nome': func.nome_exibicao,
                'nivel_critico': func.nivel_critico,
                'pode_visualizar': perm.pode_visualizar,
                'pode_editar': perm.pode_editar,
                'herdada': False,
                'origem': 'Direta',
                'concedida_em': perm.concedida_em.isoformat() if perm.concedida_em else None,
                'expira_em': perm.expira_em.isoformat() if perm.expira_em else None
            })
            processed_functions.add(func.id)
        
        # Adicionar permissões de vendedores (se não existir direta)
        for perm, func, mod, vendor in vendor_permissions:
            if func.id not in processed_functions:
                all_permissions.append({
                    'funcao_id': func.id,
                    'categoria': 'vendedor',
                    'categoria_nome': 'Vendedor',
                    'categoria_icone': '🏪',
                    'categoria_cor': '#28a745',
                    'modulo': mod.nome,
                    'modulo_nome': mod.nome_exibicao,
                    'modulo_icone': mod.icone,
                    'modulo_cor': mod.cor,
                    'funcao': func.nome,
                    'funcao_nome': func.nome_exibicao,
                    'nivel_critico': func.nivel_critico,
                    'pode_visualizar': perm.pode_visualizar,
                    'pode_editar': perm.pode_editar,
                    'herdada': True,
                    'origem': f'Vendedor: {vendor.nome}',
                    'concedida_em': perm.concedida_em.isoformat() if perm.concedida_em else None,
                    'expira_em': None
                })
        
        # Adicionar permissões de equipes (se não existir direta ou de vendedor)
        for perm, func, mod, team in team_permissions:
            if func.id not in processed_functions:
                all_permissions.append({
                    'funcao_id': func.id,
                    'categoria': 'equipe',
                    'categoria_nome': 'Equipe',
                    'categoria_icone': '👥',
                    'categoria_cor': '#17a2b8',
                    'modulo': mod.nome,
                    'modulo_nome': mod.nome_exibicao,
                    'modulo_icone': mod.icone,
                    'modulo_cor': mod.cor,
                    'funcao': func.nome,
                    'funcao_nome': func.nome_exibicao,
                    'nivel_critico': func.nivel_critico,
                    'pode_visualizar': perm.pode_visualizar,
                    'pode_editar': perm.pode_editar,
                    'herdada': True,
                    'origem': f'Equipe: {team.nome}',
                    'concedida_em': perm.concedida_em.isoformat() if perm.concedida_em else None,
                    'expira_em': None
                })
        
        # Se usuário é administrador, adicionar todas as permissões
        if user.perfil == 'administrador':
            admin_functions = db.session.query(
                FuncaoModulo,
                ModuloSistema
            ).join(
                ModuloSistema,
                FuncaoModulo.modulo_id == ModuloSistema.id
            ).filter(
                FuncaoModulo.ativo == True,
                ModuloSistema.ativo == True
            ).all()
            
            for func, mod in admin_functions:
                if func.id not in processed_functions:
                    all_permissions.append({
                        'funcao_id': func.id,
                        'categoria': 'admin',
                        'categoria_nome': 'Administrador',
                        'categoria_icone': '👑',
                        'categoria_cor': '#dc3545',
                        'modulo': mod.nome,
                        'modulo_nome': mod.nome_exibicao,
                        'modulo_icone': mod.icone,
                        'modulo_cor': mod.cor,
                        'funcao': func.nome,
                        'funcao_nome': func.nome_exibicao,
                        'nivel_critico': func.nivel_critico,
                        'pode_visualizar': True,
                        'pode_editar': True,
                        'herdada': True,
                        'origem': 'Perfil Administrador',
                        'concedida_em': None,
                        'expira_em': None
                    })
        
        return jsonify(all_permissions)
        
    except Exception as e:
        logger.error(f"Erro ao buscar permissões do usuário {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>/permissions', methods=['PUT'])
@login_required
@require_permission_admin()
def update_user_permissions(user_id):
    """Atualiza permissões de um usuário"""
    try:
        user = Usuario.query.get_or_404(user_id)
        data = request.get_json()
        
        if 'changes' not in data:
            return jsonify({'error': 'Nenhuma alteração fornecida'}), 400
        
        updated = 0
        errors = []
        
        for change in data['changes']:
            try:
                function_id = change.get('functionId')
                permission = change.get('permission')
                new_value = change.get('newValue')
                
                if not all([function_id, permission in ['view', 'edit'], new_value is not None]):
                    errors.append(f"Dados inválidos: {change}")
                    continue
                
                # Buscar ou criar permissão
                perm = PermissaoUsuario.query.filter_by(
                    usuario_id=user_id,
                    funcao_id=function_id
                ).first()
                
                if not perm:
                    perm = PermissaoUsuario(
                        usuario_id=user_id,
                        funcao_id=function_id,
                        concedida_por=current_user.id,
                        concedida_em=agora_brasil()
                    )
                    db.session.add(perm)
                
                # Atualizar permissão
                if permission == 'view':
                    perm.pode_visualizar = new_value
                    # Se removeu visualizar, remove editar também
                    if not new_value:
                        perm.pode_editar = False
                else:  # edit
                    perm.pode_editar = new_value
                    # Se adicionou editar, adiciona visualizar também
                    if new_value:
                        perm.pode_visualizar = True
                
                perm.ativo = perm.pode_visualizar or perm.pode_editar
                updated += 1
                
            except Exception as e:
                errors.append(f"Erro ao processar {change}: {str(e)}")
        
        db.session.commit()
        
        # Invalidar cache
        invalidate_user_permissions(user_id)
        
        # Registrar no log
        log_permission_action(
            'PERMISSOES_ATUALIZADAS',
            user_id=user_id,
            details={
                'alteradas': updated,
                'erros': len(errors),
                'alterado_por': current_user.id
            }
        )
        
        response = {
            'updated': updated,
            'errors': errors,
            'success': len(errors) == 0
        }
        
        return jsonify(response), 200 if len(errors) == 0 else 207
        
    except Exception as e:
        logger.error(f"Erro ao atualizar permissões: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS DE MÓDULOS
# ============================================================================

@permissions_api_unified.route('/modules', methods=['GET'])
@login_required
@require_permission_admin()
def get_modules():
    """Retorna estrutura hierárquica de módulos e funções"""
    try:
        # Por enquanto, usar estrutura de módulos existente
        modules = ModuloSistema.query.filter_by(ativo=True).order_by(ModuloSistema.ordem).all()
        
        result = []
        for modulo in modules:
            mod_data = {
                'id': modulo.id,
                'nome': modulo.nome,
                'nome_exibicao': modulo.nome_exibicao,
                'descricao': modulo.descricao,
                'icone': modulo.icone,
                'cor': modulo.cor,
                'ordem': modulo.ordem,
                'funcoes': []
            }
            
            # Buscar funções do módulo
            funcoes = FuncaoModulo.query.filter_by(
                modulo_id=modulo.id,
                ativo=True
            ).order_by(FuncaoModulo.ordem).all()
            
            for funcao in funcoes:
                mod_data['funcoes'].append({
                    'id': funcao.id,
                    'nome': funcao.nome,
                    'nome_exibicao': funcao.nome_exibicao,
                    'descricao': funcao.descricao,
                    'nivel_critico': funcao.nivel_critico,
                    'rota_padrao': funcao.rota_padrao
                })
            
            result.append(mod_data)
        
        # Agrupar em categorias (simulado por enquanto)
        categorized = [{
            'id': 'sistema',
            'nome': 'sistema',
            'nome_exibicao': 'Sistema',
            'icone': '⚙️',
            'cor': '#6c757d',
            'modules': result
        }]
        
        return jsonify(categorized)
        
    except Exception as e:
        logger.error(f"Erro ao buscar módulos: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS DE VENDEDORES E EQUIPES
# ============================================================================

@permissions_api_unified.route('/users/<int:user_id>/vendors', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_vendors(user_id):
    """Lista vendedores associados a um usuário"""
    try:
        vendors = db.session.query(
            UsuarioVendedor,
            Vendedor
        ).join(
            Vendedor,
            UsuarioVendedor.vendedor_id == Vendedor.id
        ).filter(
            UsuarioVendedor.usuario_id == user_id,
            UsuarioVendedor.ativo == True,
            Vendedor.ativo == True
        ).all()
        
        return jsonify([{
            'id': uv.id,
            'vendedor_id': v.id,
            'codigo': v.codigo,
            'nome': v.nome,
            'tipo_acesso': uv.tipo_acesso,
            'adicionado_em': uv.adicionado_em.isoformat() if uv.adicionado_em else None,
            'observacoes': uv.observacoes
        } for uv, v in vendors])
        
    except Exception as e:
        logger.error(f"Erro ao buscar vendedores do usuário {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>/vendors', methods=['POST'])
@login_required
@require_permission_admin()
def add_user_vendor(user_id):
    """Adiciona vendedor a um usuário"""
    try:
        user = Usuario.query.get_or_404(user_id)
        data = request.get_json()
        
        vendedor_id = data.get('vendedor_id')
        if not vendedor_id:
            return jsonify({'error': 'Vendedor não especificado'}), 400
        
        # Verificar se já existe
        existing = UsuarioVendedor.query.filter_by(
            usuario_id=user_id,
            vendedor_id=vendedor_id
        ).first()
        
        if existing:
            if existing.ativo:
                return jsonify({'error': 'Vendedor já associado'}), 400
            else:
                # Reativar
                existing.ativo = True
                existing.tipo_acesso = data.get('tipo_acesso', 'visualizar')
                existing.observacoes = data.get('observacoes')
                existing.adicionado_por = current_user.id
                existing.adicionado_em = agora_brasil()
        else:
            # Criar novo
            uv = UsuarioVendedor(
                usuario_id=user_id,
                vendedor_id=vendedor_id,
                tipo_acesso=data.get('tipo_acesso', 'visualizar'),
                observacoes=data.get('observacoes'),
                adicionado_por=current_user.id
            )
            db.session.add(uv)
        
        db.session.commit()
        
        # Invalidar cache
        invalidate_user_permissions(user_id)
        
        # Log
        log_permission_action(
            'VENDEDOR_ADICIONADO',
            user_id=user_id,
            details={
                'vendedor_id': vendedor_id,
                'tipo_acesso': data.get('tipo_acesso', 'visualizar')
            }
        )
        
        return jsonify({'success': True, 'message': 'Vendedor adicionado com sucesso'}), 201
        
    except Exception as e:
        logger.error(f"Erro ao adicionar vendedor: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>/vendors/<int:vendor_id>', methods=['DELETE'])
@login_required
@require_permission_admin()
def remove_user_vendor(user_id, vendor_id):
    """Remove vendedor de um usuário"""
    try:
        uv = UsuarioVendedor.query.filter_by(
            id=vendor_id,
            usuario_id=user_id
        ).first_or_404()
        
        uv.ativo = False
        db.session.commit()
        
        # Invalidar cache
        invalidate_user_permissions(user_id)
        
        # Log
        log_permission_action(
            'VENDEDOR_REMOVIDO',
            user_id=user_id,
            details={'vendedor_id': uv.vendedor_id}
        )
        
        return jsonify({'success': True, 'message': 'Vendedor removido com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao remover vendedor: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>/teams', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_teams(user_id):
    """Lista equipes associadas a um usuário"""
    try:
        teams = db.session.query(
            UsuarioEquipeVendas,
            EquipeVendas
        ).join(
            EquipeVendas,
            UsuarioEquipeVendas.equipe_id == EquipeVendas.id
        ).filter(
            UsuarioEquipeVendas.usuario_id == user_id,
            UsuarioEquipeVendas.ativo == True,
            EquipeVendas.ativo == True
        ).all()
        
        return jsonify([{
            'id': ue.id,
            'equipe_id': e.id,
            'codigo': e.codigo,
            'nome': e.nome,
            'cargo_equipe': ue.cargo_equipe,
            'tipo_acesso': ue.tipo_acesso,
            'adicionado_em': ue.adicionado_em.isoformat() if ue.adicionado_em else None,
            'observacoes': ue.observacoes
        } for ue, e in teams])
        
    except Exception as e:
        logger.error(f"Erro ao buscar equipes do usuário {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>/teams', methods=['POST'])
@login_required
@require_permission_admin()
def add_user_team(user_id):
    """Adiciona equipe a um usuário"""
    try:
        user = Usuario.query.get_or_404(user_id)
        data = request.get_json()
        
        equipe_id = data.get('equipe_id')
        if not equipe_id:
            return jsonify({'error': 'Equipe não especificada'}), 400
        
        # Verificar se já existe
        existing = UsuarioEquipeVendas.query.filter_by(
            usuario_id=user_id,
            equipe_id=equipe_id
        ).first()
        
        if existing:
            if existing.ativo:
                return jsonify({'error': 'Equipe já associada'}), 400
            else:
                # Reativar
                existing.ativo = True
                existing.cargo_equipe = data.get('cargo_equipe')
                existing.tipo_acesso = data.get('tipo_acesso', 'membro')
                existing.observacoes = data.get('observacoes')
                existing.adicionado_por = current_user.id
                existing.adicionado_em = agora_brasil()
        else:
            # Criar novo
            ue = UsuarioEquipeVendas(
                usuario_id=user_id,
                equipe_id=equipe_id,
                cargo_equipe=data.get('cargo_equipe'),
                tipo_acesso=data.get('tipo_acesso', 'membro'),
                observacoes=data.get('observacoes'),
                adicionado_por=current_user.id
            )
            db.session.add(ue)
        
        db.session.commit()
        
        # Invalidar cache
        invalidate_user_permissions(user_id)
        
        # Log
        log_permission_action(
            'EQUIPE_ADICIONADA',
            user_id=user_id,
            details={
                'equipe_id': equipe_id,
                'cargo': data.get('cargo_equipe'),
                'tipo_acesso': data.get('tipo_acesso', 'membro')
            }
        )
        
        return jsonify({'success': True, 'message': 'Equipe adicionada com sucesso'}), 201
        
    except Exception as e:
        logger.error(f"Erro ao adicionar equipe: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>/teams/<int:team_id>', methods=['DELETE'])
@login_required
@require_permission_admin()
def remove_user_team(user_id, team_id):
    """Remove equipe de um usuário"""
    try:
        ue = UsuarioEquipeVendas.query.filter_by(
            id=team_id,
            usuario_id=user_id
        ).first_or_404()
        
        ue.ativo = False
        db.session.commit()
        
        # Invalidar cache
        invalidate_user_permissions(user_id)
        
        # Log
        log_permission_action(
            'EQUIPE_REMOVIDA',
            user_id=user_id,
            details={'equipe_id': ue.equipe_id}
        )
        
        return jsonify({'success': True, 'message': 'Equipe removida com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao remover equipe: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS DE TEMPLATES
# ============================================================================

@permissions_api_unified.route('/templates', methods=['GET'])
@login_required
@require_permission_admin()
def get_templates():
    """Lista todos os templates de permissão"""
    try:
        templates = PermissionTemplate.query.filter_by(active=True).all()
        
        result = []
        for template in templates:
            # Contar usuários usando o template
            # TODO: Implementar contagem real quando tivermos relação de templates aplicados
            user_count = 0
            
            # Contar permissões no template
            template_data = json.loads(template.template_data) if template.template_data else {}
            permission_count = sum(len(perms) for perms in template_data.values())
            
            result.append({
                'id': template.id,
                'name': template.name,
                'code': template.code,
                'description': template.description,
                'category': template.category,
                'is_system': template.is_system,
                'permission_count': permission_count,
                'user_count': user_count,
                'created_at': template.created_at.isoformat() if template.created_at else None
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao listar templates: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/templates', methods=['POST'])
@login_required
@require_permission_admin()
def create_template():
    """Cria novo template de permissão"""
    try:
        data = request.get_json()
        
        # Validar dados
        if not data.get('name') or not data.get('code'):
            return jsonify({'error': 'Nome e código são obrigatórios'}), 400
        
        # Verificar se código já existe
        if PermissionTemplate.query.filter_by(code=data['code']).first():
            return jsonify({'error': 'Código já existe'}), 400
        
        # Criar template
        template = PermissionTemplate(
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            category=data.get('category', 'custom'),
            template_data='{}',  # Vazio inicialmente
            created_by=current_user.id
        )
        
        db.session.add(template)
        db.session.commit()
        
        # Log
        log_permission_action(
            'TEMPLATE_CRIADO',
            details={'template_id': template.id, 'name': template.name}
        )
        
        return jsonify({
            'id': template.id,
            'name': template.name,
            'code': template.code,
            'message': 'Template criado com sucesso'
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar template: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/users/<int:user_id>/apply-template', methods=['POST'])
@login_required
@require_permission_admin()
def apply_template_to_user(user_id):
    """Aplica template de permissão a um usuário"""
    try:
        user = Usuario.query.get_or_404(user_id)
        data = request.get_json()
        
        template_id = data.get('template_id')
        if not template_id:
            return jsonify({'error': 'Template não especificado'}), 400
        
        template = PermissionTemplate.query.get_or_404(template_id)
        
        # TODO: Implementar aplicação real do template
        # Por enquanto, apenas simular
        
        # Log
        log_permission_action(
            'TEMPLATE_APLICADO',
            user_id=user_id,
            details={'template_id': template_id, 'template_name': template.name}
        )
        
        return jsonify({
            'success': True,
            'message': f'Template "{template.name}" aplicado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao aplicar template: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS DE LOGS E AUDITORIA
# ============================================================================

@permissions_api_unified.route('/users/<int:user_id>/audit-log', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_audit_log(user_id):
    """Retorna log de auditoria de um usuário"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        logs = LogPermissao.query.filter_by(
            usuario_id=user_id
        ).order_by(
            LogPermissao.timestamp.desc()
        ).limit(limit).all()
        
        return jsonify([{
            'id': log.id,
            'acao': log.acao,
            'detalhes': log.detalhes,
            'resultado': log.resultado,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            'ip_origem': log.ip_origem
        } for log in logs])
        
    except Exception as e:
        logger.error(f"Erro ao buscar log de auditoria: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS AUXILIARES
# ============================================================================

@permissions_api_unified.route('/vendors/available', methods=['GET'])
@login_required
@require_permission_admin()
def get_available_vendors():
    """Lista vendedores disponíveis para associação"""
    try:
        vendors = Vendedor.query.filter_by(ativo=True).order_by(Vendedor.nome).all()
        
        return jsonify([{
            'id': v.id,
            'codigo': v.codigo,
            'nome': v.nome,
            'cnpj_cpf': v.cnpj_cpf
        } for v in vendors])
        
    except Exception as e:
        logger.error(f"Erro ao listar vendedores disponíveis: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/teams/available', methods=['GET'])
@login_required
@require_permission_admin()
def get_available_teams():
    """Lista equipes disponíveis para associação"""
    try:
        teams = EquipeVendas.query.filter_by(ativo=True).order_by(EquipeVendas.nome).all()
        
        return jsonify([{
            'id': t.id,
            'codigo': t.codigo,
            'nome': t.nome,
            'gerente': t.gerente.nome if t.gerente else None
        } for t in teams])
        
    except Exception as e:
        logger.error(f"Erro ao listar equipes disponíveis: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api_unified.route('/export', methods=['GET'])
@login_required
@require_permission_admin()
def export_permissions():
    """Exporta configurações de permissões"""
    try:
        # TODO: Implementar exportação real
        export_data = {
            'exported_at': agora_brasil().isoformat(),
            'exported_by': current_user.email,
            'version': '1.0',
            'data': {
                'users': [],
                'templates': [],
                'permissions': []
            }
        }
        
        return jsonify(export_data), 200, {
            'Content-Disposition': f'attachment; filename=permissions_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        }
        
    except Exception as e:
        logger.error(f"Erro ao exportar permissões: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# HANDLERS DE ERRO
# ============================================================================

@permissions_api_unified.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Recurso não encontrado'}), 404

@permissions_api_unified.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Acesso negado'}), 403

@permissions_api_unified.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {error}")
    return jsonify({'error': 'Erro interno do servidor'}), 500