from flask import Blueprint, render_template, redirect, url_for, flash, session, abort, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import logging
from app.utils.timezone import agora_utc_naive

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
                usuario.ultimo_login = agora_utc_naive()
                db.session.commit()
                
                # ✅ CORREÇÃO: Configura sessão permanente (4 horas)
                session.permanent = True
                login_user(usuario, remember=True)

                # Redirecionamento baseado no perfil do usuário
                if usuario.perfil == 'vendedor':
                    # Vendedores vão direto para o dashboard comercial
                    return redirect(url_for('comercial.dashboard_diretoria'))
                # Sistema e 100% Nacom exceto 5 dominios isolados. Quem nao tem
                # Nacom cai direto no dashboard do dominio ao qual pertence.
                if not usuario.sistema_logistica and usuario.perfil != 'administrador':
                    from app.auth.utils import url_primeiro_dashboard_disponivel
                    url_destino = url_primeiro_dashboard_disponivel(usuario)
                    if url_destino:
                        return redirect(url_destino)
                    flash('Seu usuario nao tem acesso a nenhum modulo. Contate o administrador.', 'danger')
                    return redirect(url_for('auth.logout'))
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

@auth_bp.route('/registro-motochefe-sp', methods=['GET', 'POST'])
def registro_motochefe_sp():
    """Página pública de registro - Motochefe SP (módulo Lojas HORA)"""
    form = RegistroForm()
    # Perfil padrão: financeiro (não afeta acesso às lojas, que depende apenas de sistema_lojas)
    if not form.is_submitted():
        form.perfil.data = 'financeiro'
    if form.validate_on_submit():
        # Verificar se email já existe
        usuario_existente = db.session.query(Usuario).filter_by(email=form.email.data).first()
        if usuario_existente:
            flash('Este e-mail já está cadastrado.', 'danger')
            return render_template('auth/registro.html', form=form, sistema='lojas_sp')

        # Criar novo usuário para sistema Lojas HORA (Motochefe SP)
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            empresa=form.empresa.data,
            cargo=form.cargo.data,
            telefone=form.telefone.data,
            perfil=form.perfil.data,
            status='pendente',
            sistema_logistica=False,
            sistema_motochefe=False,
            sistema_lojas=True
        )
        usuario.set_senha(form.senha.data)

        db.session.add(usuario)
        db.session.commit()

        flash('Solicitação de acesso ao Motochefe SP enviada! Aguarde aprovação da administração.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html', form=form, sistema='lojas_sp')

@auth_bp.route('/registro-motos-assai', methods=['GET', 'POST'])
def registro_motos_assai():
    """Página pública de registro - Motos Assaí (operação Q.P.A. → Sendas/Assaí)."""
    form = RegistroForm()
    # Perfil padrão: financeiro (acesso ao módulo é gated apenas por sistema_motos_assai)
    if not form.is_submitted():
        form.perfil.data = 'financeiro'
    if form.validate_on_submit():
        # Verificar se email já existe
        usuario_existente = db.session.query(Usuario).filter_by(email=form.email.data).first()
        if usuario_existente:
            flash('Este e-mail já está cadastrado.', 'danger')
            return render_template('auth/registro.html', form=form, sistema='motos_assai')

        # Criar novo usuário para sistema Motos Assaí
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            empresa=form.empresa.data,
            cargo=form.cargo.data,
            telefone=form.telefone.data,
            perfil=form.perfil.data,
            status='pendente',
            sistema_logistica=False,
            sistema_motochefe=False,
            sistema_lojas=False,
            sistema_motos_assai=True
        )
        usuario.set_senha(form.senha.data)

        db.session.add(usuario)
        db.session.commit()

        flash('Solicitação de acesso ao Sistema Motos Assaí enviada! Aguarde aprovação da administração.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html', form=form, sistema='motos_assai')

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
    
    # Popular choices de lojas HORA (todas + ativas)
    form.loja_hora_id.choices = _obter_choices_lojas_hora()

    if form.validate_on_submit():
        usuario.perfil = form.perfil.data
        vendedor_vinculado = form.vendedor_vinculado.data if form.vendedor_vinculado.data else None
        usuario.aprovar(current_user.email, vendedor_vinculado)
        usuario.observacoes = form.observacoes.data
        usuario.sistema_logistica = form.sistema_logistica.data  # ✅ NOVO
        usuario.sistema_motochefe = form.sistema_motochefe.data  # ✅ NOVO
        usuario.sistema_carvia = form.sistema_carvia.data
        usuario.sistema_lojas = form.sistema_lojas.data
        usuario.sistema_motos_assai = form.sistema_motos_assai.data
        usuario.loja_hora_id = int(form.loja_hora_id.data) if form.loja_hora_id.data else None
        usuario.acesso_comissao_carvia = form.acesso_comissao_carvia.data
        usuario.sistema_remessa_vortx = form.sistema_remessa_vortx.data

        db.session.commit()
        flash(f'Usuário {usuario.nome} aprovado com sucesso!', 'success')
        return redirect(url_for('auth.usuarios_pendentes'))

    # Pré-preencher com dados do usuário
    form.perfil.data = usuario.perfil
    form.sistema_logistica.data = usuario.sistema_logistica  # ✅ NOVO
    form.sistema_motochefe.data = usuario.sistema_motochefe  # ✅ NOVO
    form.sistema_carvia.data = usuario.sistema_carvia
    form.sistema_lojas.data = usuario.sistema_lojas
    form.sistema_motos_assai.data = usuario.sistema_motos_assai
    form.loja_hora_id.data = str(usuario.loja_hora_id) if usuario.loja_hora_id else ''
    form.acesso_comissao_carvia.data = usuario.acesso_comissao_carvia
    form.sistema_remessa_vortx.data = usuario.sistema_remessa_vortx

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
    form.loja_hora_id.choices = _obter_choices_lojas_hora()

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
        usuario.sistema_carvia = form.sistema_carvia.data
        usuario.sistema_lojas = form.sistema_lojas.data
        usuario.sistema_motos_assai = form.sistema_motos_assai.data
        usuario.loja_hora_id = int(form.loja_hora_id.data) if form.loja_hora_id.data else None
        usuario.acesso_comissao_carvia = form.acesso_comissao_carvia.data
        usuario.sistema_remessa_vortx = form.sistema_remessa_vortx.data
        usuario.whatsapp_autorizado = form.whatsapp_autorizado.data
        usuario.agente_fable5 = form.agente_fable5.data

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
    form.sistema_carvia.data = usuario.sistema_carvia
    form.sistema_lojas.data = usuario.sistema_lojas
    form.sistema_motos_assai.data = usuario.sistema_motos_assai
    form.loja_hora_id.data = str(usuario.loja_hora_id) if usuario.loja_hora_id else ''
    form.acesso_comissao_carvia.data = usuario.acesso_comissao_carvia
    form.sistema_remessa_vortx.data = usuario.sistema_remessa_vortx
    form.whatsapp_autorizado.data = usuario.whatsapp_autorizado
    form.agente_fable5.data = usuario.agente_fable5

    return render_template('auth/editar_usuario.html', form=form, usuario=usuario)

def _obter_choices_lojas_hora():
    """Retorna choices para SelectField de loja HORA. [('', 'Todas'), ...].

    Lazy import para evitar circular (app.hora depende de app core).
    Tolerante a tabela hora_loja ainda inexistente (retorna só 'Todas').
    """
    try:
        from app.hora.models import HoraLoja
        lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()
        return [('', 'Todas as lojas')] + [(str(l.id), f'{l.nome} ({l.cnpj})') for l in lojas]
    except Exception:
        return [('', 'Todas as lojas')]


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


# ════════════════════════════════════════════════════════════════
# Vinculacao Microsoft Teams (Fase A — plano teams-melhorias 2026-06-10)
# ════════════════════════════════════════════════════════════════

# Alfabeto sem caracteres ambiguos (sem I/O/0/1). Primeiro char SEMPRE letra:
# o fast-path 'vincular CODIGO' rejeita digitos puros para nao colidir com
# numeros de pedido (ver app/agente/sdk/vincular_teams_fastpath.py).
_TEAMS_CODIGO_LETRAS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
_TEAMS_CODIGO_ALFABETO = _TEAMS_CODIGO_LETRAS + '23456789'
TEAMS_CODIGO_TTL_MINUTOS = 10


@auth_bp.route('/vincular-teams', methods=['GET', 'POST'])
@login_required
def vincular_teams():
    """Tela de pareamento Teams <-> Web: gera codigo de uso unico (TTL 10 min).

    O usuario logado gera o codigo aqui e envia "vincular ABC123" ao bot no
    Teams. O fast-path valida o hash e grava Usuario.teams_user_id (AAD) —
    prova de posse das DUAS contas, independe de e-mail correto no cadastro.
    """
    import hashlib
    import secrets
    from datetime import timedelta
    from app.auth.models import TeamsVinculoCodigo

    # Guard explicito (login_required vira no-op com LOGIN_DISABLED em testes)
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    codigo_gerado = None
    if request.method == 'POST':
        # Invalida codigos anteriores nao usados deste usuario (1 ativo por vez)
        TeamsVinculoCodigo.query.filter(
            TeamsVinculoCodigo.user_id == current_user.id,
            TeamsVinculoCodigo.used_at.is_(None),
        ).delete(synchronize_session=False)

        codigo_gerado = secrets.choice(_TEAMS_CODIGO_LETRAS) + ''.join(
            secrets.choice(_TEAMS_CODIGO_ALFABETO) for _ in range(5)
        )
        vc = TeamsVinculoCodigo(
            user_id=current_user.id,
            codigo_hash=hashlib.sha256(codigo_gerado.encode()).hexdigest(),
            expires_at=agora_utc_naive() + timedelta(minutes=TEAMS_CODIGO_TTL_MINUTOS),
        )
        db.session.add(vc)
        db.session.commit()
        logger.info(f"[TEAMS-VINCULO] Codigo gerado para user_id={current_user.id}")

    return render_template(
        'auth/vincular_teams.html',
        codigo=codigo_gerado,
        ttl_minutos=TEAMS_CODIGO_TTL_MINUTOS,
        usuario=current_user,
    )


@auth_bp.route('/usuarios/<int:user_id>/desvincular-teams', methods=['POST'])
@login_required
def desvincular_teams(user_id):
    """Remove o vinculo Teams de um usuario (admin — tela editar usuario)."""
    if not current_user.is_authenticated or not current_user.pode_aprovar_usuarios():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))

    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        abort(404)
    usuario.teams_user_id = None
    usuario.teams_vinculo_origem = None
    db.session.commit()
    flash(f'Vinculo Teams de {usuario.nome} removido.', 'success')
    return redirect(url_for('auth.editar_usuario', user_id=user_id))
