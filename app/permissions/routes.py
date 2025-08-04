"""
Sistema de Permissões Simples - Rotas de Gerenciamento
======================================================

Rotas para gerenciar vendedores e equipes dos usuários.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from app.auth.models import Usuario
from app.permissions.models import UserVendedor, UserEquipe, EquipeVendas
from app.faturamento.models import RelatorioFaturamentoImportado
from app.carteira.models import CarteiraPrincipal
from app.permissions.sync_equipes import sincronizar_equipe_por_nome
import logging

logger = logging.getLogger(__name__)
permissions_bp = Blueprint('permissions', __name__, url_prefix='/permissions')

@permissions_bp.route('/')
@login_required
def index():
    """Redireciona para vendedores"""
    # Apenas admin e gerente_comercial podem acessar
    if current_user.perfil not in ['administrador', 'gerente_comercial']:
        flash('Acesso restrito a administradores', 'error')
        return redirect(url_for('main.dashboard'))
    
    return redirect(url_for('permissions.vendedores_vanilla'))


@permissions_bp.route('/vendedores')
@login_required
def vendedores_vanilla():
    """Lista de usuários para configurar vendedores e equipes"""
    # Apenas admin e gerente_comercial podem acessar
    if current_user.perfil not in ['administrador', 'gerente_comercial']:
        flash('Acesso restrito a administradores', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Listar usuários ativos (exceto admins)
        usuarios = Usuario.query.filter(
            Usuario.status == 'ativo',
            Usuario.perfil != 'administrador'
        ).order_by(Usuario.nome).all()
        
        return render_template('permissions/vendedores_simples.html',
                               usuarios=usuarios)
    except Exception as e:
        logger.error(f"Erro ao carregar página de vendedores: {e}")
        flash('Erro ao carregar configuração de vendedores', 'error')
        return redirect(url_for('main.dashboard'))


@permissions_bp.route('/usuarios/<int:user_id>/configurar')
@login_required
def configurar_usuario(user_id):
    """Página para configurar vendedores e equipes de um usuário"""
    # Apenas admin e gerente_comercial podem acessar
    if current_user.perfil not in ['administrador', 'gerente_comercial']:
        flash('Acesso restrito a administradores', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        usuario = Usuario.query.get_or_404(user_id)
        
        # Buscar vendedores únicos do faturamento e carteira
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
        
        vendedores = sorted(list(vendedores_set))
        
        # Buscar equipes únicas do faturamento e carteira
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
        
        equipes = sorted(list(equipes_set))
        
        # Buscar vendedores e equipes já selecionados
        vendedores_selecionados = []
        user_vendors = UserVendedor.query.filter_by(
            user_id=user_id,
            ativo=True
        ).all()
        
        for uv in user_vendors:
            if uv.vendedor_id:
                from app.permissions.models import Vendedor
                vendedor = Vendedor.query.get(uv.vendedor_id)
                if vendedor:
                    vendedores_selecionados.append(vendedor.nome)
            elif uv.observacoes:
                vendedores_selecionados.append(uv.observacoes)
        
        equipes_selecionadas = []
        user_teams = UserEquipe.query.filter_by(
            user_id=user_id,
            ativo=True
        ).all()
        
        for ut in user_teams:
            if ut.equipe_id:
                equipe = EquipeVendas.query.get(ut.equipe_id)
                if equipe:
                    equipes_selecionadas.append(equipe.nome)
            elif ut.observacoes:
                equipes_selecionadas.append(ut.observacoes)
        
        return render_template('permissions/configurar_usuario.html',
                               usuario=usuario,
                               vendedores=vendedores,
                               equipes=equipes,
                               vendedores_selecionados=vendedores_selecionados,
                               equipes_selecionadas=equipes_selecionadas)
    
    except Exception as e:
        logger.error(f"Erro ao carregar configuração do usuário: {e}")
        flash('Erro ao carregar configuração', 'error')
        return redirect(url_for('permissions.vendedores_vanilla'))


@permissions_bp.route('/usuarios/<int:user_id>/salvar', methods=['POST'])
@login_required
def salvar_configuracao(user_id):
    """Salvar configuração de vendedores e equipes"""
    # Apenas admin e gerente_comercial podem acessar
    if current_user.perfil not in ['administrador', 'gerente_comercial']:
        flash('Acesso restrito a administradores', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Obter vendedores e equipes selecionados
        vendedores_selecionados = request.form.getlist('vendedores')
        equipes_selecionadas = request.form.getlist('equipes')
        
        # Remover vendedores antigos
        UserVendedor.query.filter_by(user_id=user_id).delete()
        
        # Adicionar novos vendedores
        for vendedor_nome in vendedores_selecionados:
            # Verificar se existe na tabela Vendedor
            from app.permissions.models import Vendedor
            vendedor = Vendedor.query.filter_by(nome=vendedor_nome).first()
            
            if vendedor:
                uv = UserVendedor(
                    user_id=user_id,
                    vendedor_id=vendedor.id,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            else:
                # Salvar nome no campo observacoes
                uv = UserVendedor(
                    user_id=user_id,
                    vendedor_id=None,
                    observacoes=vendedor_nome,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            db.session.add(uv)
        
        # Remover equipes antigas
        UserEquipe.query.filter_by(user_id=user_id).delete()
        
        # Adicionar novas equipes
        for equipe_nome in equipes_selecionadas:
            # Sincronizar ou criar equipe
            equipe = sincronizar_equipe_por_nome(equipe_nome, current_user.id)
            
            if equipe:
                ue = UserEquipe(
                    user_id=user_id,
                    equipe_id=equipe.id,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            else:
                # Salvar nome no campo observacoes
                ue = UserEquipe(
                    user_id=user_id,
                    equipe_id=None,
                    observacoes=equipe_nome,
                    ativo=True,
                    adicionado_por=current_user.id
                )
            db.session.add(ue)
        
        db.session.commit()
        
        flash('Vendedores e equipes salvos com sucesso!', 'success')
        return redirect(url_for('permissions.vendedores_vanilla'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar configuração: {e}")
        flash('Erro ao salvar configuração', 'error')
        return redirect(url_for('permissions.configurar_usuario', user_id=user_id))