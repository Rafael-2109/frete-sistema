"""
API Simplificada de Permissões
==============================

Endpoints essenciais para gerenciar vendedores e equipes de usuários.
Toda a complexidade hierárquica foi removida.
"""

import logging
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import or_
from app import db
from app.auth.models import Usuario
from app.permissions.models import UserVendedor, UserEquipe, EquipeVendas, Vendedor
from app.faturamento.models import RelatorioFaturamentoImportado
from app.carteira.models import CarteiraPrincipal
from app.permissions.sync_equipes import sincronizar_equipe_por_nome

logger = logging.getLogger(__name__)

# Criar blueprint
permissions_api = Blueprint('permissions_api', __name__, url_prefix='/api/v1/permissions')

# ============================================================================
# DECORADORES
# ============================================================================

def require_permission_admin():
    """Decorador para garantir que usuário tem permissão de administrar permissões"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.perfil not in ['administrador', 'gerente_comercial']:
                abort(403, 'Sem permissão para gerenciar permissões')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================================
# ENDPOINTS DE USUÁRIOS
# ============================================================================

@permissions_api.route('/users', methods=['GET'])
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

@permissions_api.route('/users/<int:user_id>', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_details(user_id):
    """Retorna detalhes de um usuário"""
    try:
        user = Usuario.query.get_or_404(user_id)
        
        # Contar vendedores e equipes
        vendor_count = UserVendedor.query.filter_by(
            user_id=user_id,
            ativo=True
        ).count()
        
        team_count = UserEquipe.query.filter_by(
            user_id=user_id,
            ativo=True
        ).count()
        
        return jsonify({
            'success': True,
            'user': {
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
                    'vendors': vendor_count,
                    'teams': team_count
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do usuário {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENDPOINTS DE VENDEDORES E EQUIPES
# ============================================================================

@permissions_api.route('/users/<int:user_id>/vendors', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_vendors(user_id):
    """Lista vendedores associados a um usuário"""
    try:
        # Vendedores salvos do usuário
        user_vendors_obj = UserVendedor.query.filter_by(
            user_id=user_id,
            ativo=True
        ).all()
        
        # Extrair nomes dos vendedores salvos
        vendedores_salvos = []
        for uv in user_vendors_obj:
            if uv.vendedor_id:
                vendedor = db.session.get(Vendedor,uv.vendedor_id) if uv.vendedor_id else None
                if vendedor:
                    vendedores_salvos.append(vendedor.nome)
            elif uv.observacoes:
                vendedores_salvos.append(uv.observacoes)
        
        # Buscar vendedores distintos do faturamento e carteira
        vendedores_faturamento = db.session.query(
            RelatorioFaturamentoImportado.vendedor
        ).filter(
            RelatorioFaturamentoImportado.vendedor.isnot(None),
            RelatorioFaturamentoImportado.vendedor != ''
        ).distinct().all()
        
        vendedores_carteira = db.session.query(
            CarteiraPrincipal.vendedor  
        ).filter(
            CarteiraPrincipal.vendedor.isnot(None),
            CarteiraPrincipal.vendedor != ''
        ).distinct().all()
        
        # Combinar vendedores únicos
        vendedores_set = set()
        for (v,) in vendedores_faturamento:
            if v:
                vendedores_set.add(v)
        for (v,) in vendedores_carteira:
            if v:
                vendedores_set.add(v)
        
        # Montar lista final
        todos_vendedores = []
        for vendedor_nome in sorted(vendedores_set):
            todos_vendedores.append({
                'id': vendedor_nome,  # Usar o nome como ID
                'nome': vendedor_nome,
                'codigo': vendedor_nome
            })
        
        return jsonify({
            'user_vendors': [{'vendedor_id': v, 'nome': v} for v in vendedores_salvos],
            'all_vendors': todos_vendedores
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar vendedores do usuário {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api.route('/users/<int:user_id>/teams', methods=['GET'])
@login_required
@require_permission_admin()
def get_user_teams(user_id):
    """Lista equipes associadas a um usuário"""
    try:
        # Equipes salvas do usuário
        user_teams_obj = UserEquipe.query.filter_by(
            user_id=user_id,
            ativo=True
        ).all()
        
        # Extrair nomes das equipes salvas
        equipes_salvas = []
        for ue in user_teams_obj:
            if ue.equipe_id:
                equipe = db.session.get(EquipeVendas,ue.equipe_id) if ue.equipe_id else None
                if equipe:
                    equipes_salvas.append(equipe.nome)
            elif ue.observacoes:
                equipes_salvas.append(ue.observacoes)
        
        # Buscar equipes distintas do faturamento e carteira
        equipes_faturamento = db.session.query(
            RelatorioFaturamentoImportado.equipe_vendas
        ).filter(
            RelatorioFaturamentoImportado.equipe_vendas.isnot(None),
            RelatorioFaturamentoImportado.equipe_vendas != ''
        ).distinct().all()
        
        equipes_carteira = db.session.query(
            CarteiraPrincipal.equipe_vendas
        ).filter(
            CarteiraPrincipal.equipe_vendas.isnot(None),
            CarteiraPrincipal.equipe_vendas != ''
        ).distinct().all()
        
        # Combinar equipes únicas
        equipes_set = set()
        for (e,) in equipes_faturamento:
            if e:
                equipes_set.add(e)
        for (e,) in equipes_carteira:
            if e:
                equipes_set.add(e)
        
        # Montar lista final
        todas_equipes = []
        for equipe_nome in sorted(equipes_set):
            todas_equipes.append({
                'id': equipe_nome,  # Usar nome como ID
                'nome': equipe_nome,
                'codigo': equipe_nome
            })
        
        return jsonify({
            'user_teams': [{'nome': e} for e in equipes_salvas],
            'all_teams': todas_equipes
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar equipes do usuário {user_id}: {e}")
        return jsonify({'error': str(e)}), 500

@permissions_api.route('/users/<int:user_id>/vendors-teams', methods=['PUT'])
@login_required
@require_permission_admin()
def update_user_vendors_teams(user_id):
    """Atualizar vendedores e equipes do usuário"""
    try:
        data = request.get_json()
        vendor_names = data.get('vendor_ids', [])  # São nomes, não IDs
        team_names = data.get('team_ids', [])  # São nomes, não IDs
        
        # Remover vendedores antigos
        UserVendedor.query.filter_by(user_id=user_id).delete()
        
        # Adicionar novos vendedores
        for vendor_name in vendor_names:
            vendedor = db.session.query(Vendedor).filter_by(nome=vendor_name).first()
            
            if vendedor:
                uv = UserVendedor(
                    user_id=user_id,
                    vendedor_id=vendedor.id,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            else:
                uv = UserVendedor(
                    user_id=user_id,
                    vendedor_id=None,
                    observacoes=vendor_name,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            db.session.add(uv)
        
        # Remover equipes antigas
        UserEquipe.query.filter_by(user_id=user_id).delete()
        
        # Adicionar novas equipes
        for team_name in team_names:
            equipe = sincronizar_equipe_por_nome(team_name, current_user.id)
            
            if equipe:
                ue = UserEquipe(
                    user_id=user_id,
                    equipe_id=equipe.id,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            else:
                ue = UserEquipe(
                    user_id=user_id,
                    equipe_id=None,
                    observacoes=team_name,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            db.session.add(ue)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Vendedores e equipes atualizados com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar vendedores/equipes: {e}")
        return jsonify({'error': 'Erro ao salvar alterações'}), 500

# ============================================================================
# HANDLERS DE ERRO
# ============================================================================

@permissions_api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Recurso não encontrado'}), 404

@permissions_api.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Acesso negado'}), 403

@permissions_api.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno: {error}")
    return jsonify({'error': 'Erro interno do servidor'}), 500