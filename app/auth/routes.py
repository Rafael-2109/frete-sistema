from flask import Blueprint, render_template, redirect, url_for, flash, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import logging

from app import db
from app.auth.forms import LoginForm, RegistroForm, AprovarUsuarioForm, RejeitarUsuarioForm, EditarUsuarioForm
from app.auth.models import Usuario

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = db.session.query(Usuario).filter_by(email=form.email.data).first()
        if usuario and usuario.verificar_senha(form.senha.data):
            if usuario.is_approved:
                # Atualizar último login
                usuario.ultimo_login = datetime.utcnow()
                db.session.commit()
                
                # ✅ CORREÇÃO: Configura sessão permanente (4 horas)
                session.permanent = True
                login_user(usuario, remember=True)

                # Redirecionamento baseado no perfil do usuário
                if usuario.perfil == 'vendedor':
                    # Vendedores vão direto para o dashboard comercial
                    return redirect(url_for('comercial.dashboard_diretoria'))
                else:
                    # Outros perfis vão para o dashboard principal
                    return redirect(url_for('main.dashboard'))
            else:
                flash('Sua conta ainda não foi aprovada ou está bloqueada.', 'warning')
        else:
            flash('E-mail ou senha inválidos', 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Página pública de registro - Sistema Logística"""
    form = RegistroForm()
    if form.validate_on_submit():
        # Verificar se email já existe
        usuario_existente = db.session.query(Usuario).filter_by(email=form.email.data).first()
        if usuario_existente:
            flash('Este e-mail já está cadastrado.', 'danger')
            return render_template('auth/registro.html', form=form, sistema='logistica')

        # Criar novo usuário para sistema de logística
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            empresa=form.empresa.data,
            cargo=form.cargo.data,
            telefone=form.telefone.data,
            perfil=form.perfil.data,
            status='pendente',
            sistema_logistica=True,  # ✅ NOVO
            sistema_motochefe=False  # ✅ NOVO
        )
        usuario.set_senha(form.senha.data)

        db.session.add(usuario)
        db.session.commit()

        flash('Solicitação de acesso ao Sistema de Logística enviada! Aguarde aprovação da administração.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html', form=form, sistema='logistica')

@auth_bp.route('/registro-motochefe', methods=['GET', 'POST'])
def registro_motochefe():
    """Página pública de registro - Sistema MotoChefe"""
    form = RegistroForm()
    if form.validate_on_submit():
        # Verificar se email já existe
        usuario_existente = db.session.query(Usuario).filter_by(email=form.email.data).first()
        if usuario_existente:
            flash('Este e-mail já está cadastrado.', 'danger')
            return render_template('auth/registro.html', form=form, sistema='motochefe')

        # Criar novo usuário para sistema motochefe
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            empresa=form.empresa.data,
            cargo=form.cargo.data,
            telefone=form.telefone.data,
            perfil=form.perfil.data,
            status='pendente',
            sistema_logistica=False,  # ✅ NOVO
            sistema_motochefe=True    # ✅ NOVO
        )
        usuario.set_senha(form.senha.data)

        db.session.add(usuario)
        db.session.commit()

        flash('Solicitação de acesso ao Sistema MotoChefe enviada! Aguarde aprovação da administração.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html', form=form, sistema='motochefe')

@auth_bp.route('/usuarios/pendentes')
@login_required
def usuarios_pendentes():
    """Lista usuários pendentes de aprovação"""
    if not current_user.pode_aprovar_usuarios():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    usuarios = db.session.query(Usuario).filter_by(status='pendente').order_by(Usuario.criado_em.desc()).all()
    return render_template('auth/usuarios_pendentes.html', usuarios=usuarios)

@auth_bp.route('/usuarios/<int:user_id>/aprovar', methods=['GET', 'POST'])
@login_required
def aprovar_usuario(user_id):
    """Aprova um usuário pendente"""
    if not current_user.pode_aprovar_usuarios():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    usuario = db.session.get(Usuario,user_id)
    if not usuario:
        abort(404)
    form = AprovarUsuarioForm()
    
    # Carregar lista de vendedores para vinculação
    vendedores = obter_lista_vendedores()
    form.vendedor_vinculado.choices = [('', 'Selecione...')] + [(v, v) for v in vendedores]
    
    if form.validate_on_submit():
        usuario.perfil = form.perfil.data
        vendedor_vinculado = form.vendedor_vinculado.data if form.vendedor_vinculado.data else None
        usuario.aprovar(current_user.email, vendedor_vinculado)
        usuario.observacoes = form.observacoes.data
        usuario.sistema_logistica = form.sistema_logistica.data  # ✅ NOVO
        usuario.sistema_motochefe = form.sistema_motochefe.data  # ✅ NOVO

        db.session.commit()
        flash(f'Usuário {usuario.nome} aprovado com sucesso!', 'success')
        return redirect(url_for('auth.usuarios_pendentes'))

    # Pré-preencher com dados do usuário
    form.perfil.data = usuario.perfil
    form.sistema_logistica.data = usuario.sistema_logistica  # ✅ NOVO
    form.sistema_motochefe.data = usuario.sistema_motochefe  # ✅ NOVO

    return render_template('auth/aprovar_usuario.html', form=form, usuario=usuario)

@auth_bp.route('/usuarios/<int:user_id>/rejeitar', methods=['GET', 'POST'])
@login_required
def rejeitar_usuario(user_id):
    """Rejeita um usuário pendente"""
    if not current_user.pode_aprovar_usuarios():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    usuario = db.session.get(Usuario,user_id)
    if not usuario:
        abort(404)
    form = RejeitarUsuarioForm()
    
    if form.validate_on_submit():
        usuario.rejeitar(form.motivo.data)
        db.session.commit()
        flash(f'Usuário {usuario.nome} rejeitado.', 'warning')
        return redirect(url_for('auth.usuarios_pendentes'))
    
    return render_template('auth/rejeitar_usuario.html', form=form, usuario=usuario)

@auth_bp.route('/usuarios')
@login_required
def listar_usuarios():
    """Lista todos os usuários do sistema"""
    if not current_user.pode_aprovar_usuarios():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    usuarios = db.session.query(Usuario).order_by(Usuario.criado_em.desc()).all()
    return render_template('auth/listar_usuarios.html', usuarios=usuarios)

@auth_bp.route('/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    """Edita um usuário existente"""
    if not current_user.pode_aprovar_usuarios():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    usuario = db.session.get(Usuario,user_id)
    if not usuario:
        abort(404)
    form = EditarUsuarioForm()
    
    # Carregar lista de vendedores
    vendedores = obter_lista_vendedores()
    form.vendedor_vinculado.choices = [('', 'Selecione...')] + [(v, v) for v in vendedores]
    
    if form.validate_on_submit():
        usuario.nome = form.nome.data
        usuario.email = form.email.data
        usuario.empresa = form.empresa.data
        usuario.cargo = form.cargo.data
        usuario.telefone = form.telefone.data
        usuario.perfil = form.perfil.data
        usuario.vendedor_vinculado = form.vendedor_vinculado.data if form.vendedor_vinculado.data else None
        usuario.status = form.status.data
        usuario.observacoes = form.observacoes.data
        usuario.sistema_logistica = form.sistema_logistica.data  # ✅ NOVO
        usuario.sistema_motochefe = form.sistema_motochefe.data  # ✅ NOVO

        db.session.commit()
        flash(f'Usuário {usuario.nome} atualizado com sucesso!', 'success')
        return redirect(url_for('auth.listar_usuarios'))

    # Pré-preencher formulário
    form.nome.data = usuario.nome
    form.email.data = usuario.email
    form.empresa.data = usuario.empresa
    form.cargo.data = usuario.cargo
    form.telefone.data = usuario.telefone
    form.perfil.data = usuario.perfil
    form.vendedor_vinculado.data = usuario.vendedor_vinculado
    form.status.data = usuario.status
    form.observacoes.data = usuario.observacoes
    form.sistema_logistica.data = usuario.sistema_logistica  # ✅ NOVO
    form.sistema_motochefe.data = usuario.sistema_motochefe  # ✅ NOVO

    return render_template('auth/editar_usuario.html', form=form, usuario=usuario)

def obter_lista_vendedores():
    """Obtém lista de vendedores únicos do faturamento"""
    try:
        # Importar aqui para evitar import circular
        from app.faturamento.models import RelatorioFaturamentoImportado
        vendedores = db.session.query(RelatorioFaturamentoImportado.vendedor).distinct().filter(
            RelatorioFaturamentoImportado.vendedor.isnot(None),
            RelatorioFaturamentoImportado.vendedor != ''
        ).all()
        return sorted([v[0] for v in vendedores if v[0]])
    except Exception as e:
        print(f"Erro ao obter lista de vendedores: {e}")
        return []
