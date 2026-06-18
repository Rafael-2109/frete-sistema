"""Portal do Cliente CarVia — blueprint EXTERNO isolado (stream 5).

Auth PROPRIA por sessao (chave dedicada `carvia_portal_uid`), decorator `@portal_required`.
NUNCA usa Flask-Login `current_user`/perfis internos — um cliente externo jamais acessa o
sistema interno. Registrado em app/__init__ como blueprint separado (/portal-cliente).

Paginas: login, registrar (auto-registro -> PENDENTE), dashboard (NFs escopadas + status),
detalhe da NF (timeline das 5 etapas) e cotar frete (reuso do motor CarVia).
"""
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for, flash, session, g)

from app import db

portal_cliente_bp = Blueprint('portal_cliente', __name__, url_prefix='/portal-cliente')

SESSION_KEY = 'carvia_portal_uid'


def _current_portal_user():
    if getattr(g, '_portal_user', None) is not None:
        return g._portal_user
    uid = session.get(SESSION_KEY)
    if not uid:
        return None
    from app.carvia.models.portal import CarviaPortalUsuario, PORTAL_STATUS_ATIVO
    u = db.session.get(CarviaPortalUsuario, uid)
    if u is None or u.status != PORTAL_STATUS_ATIVO:
        session.pop(SESSION_KEY, None)
        return None
    g._portal_user = u
    return u


def portal_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _current_portal_user() is None:
            flash('Faca login para acessar o portal.', 'warning')
            return redirect(url_for('portal_cliente.login'))
        return f(*args, **kwargs)
    return wrapper


# --------------------------------------------------------------------- auth
@portal_cliente_bp.route('/login', methods=['GET', 'POST'])
def login():
    if _current_portal_user() is not None:
        return redirect(url_for('portal_cliente.dashboard'))
    if request.method == 'POST':
        from app.carvia.services.documentos.portal_auth_service import CarviaPortalAuthService
        user, motivo = CarviaPortalAuthService.autenticar(
            request.form.get('email'), request.form.get('senha'))
        if user is None:
            db.session.rollback()
            flash(motivo or 'Falha no login.', 'danger')
        else:
            db.session.commit()
            session[SESSION_KEY] = user.id
            session.permanent = True
            return redirect(url_for('portal_cliente.dashboard'))
    return render_template('carvia/portal/login.html')


@portal_cliente_bp.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        from app.carvia.services.documentos.portal_auth_service import (
            CarviaPortalAuthService, PortalAuthError)
        try:
            CarviaPortalAuthService.registrar(
                nome=request.form.get('nome'), email=request.form.get('email'),
                senha=request.form.get('senha'), telefone=request.form.get('telefone'),
                grupo_empresa=request.form.get('grupo_empresa'))
            db.session.commit()
            flash('Cadastro enviado! Sua conta sera liberada apos aprovacao da CarVia.', 'success')
            return redirect(url_for('portal_cliente.login'))
        except PortalAuthError as e:
            db.session.rollback()
            flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')
    return render_template('carvia/portal/registrar.html')


@portal_cliente_bp.route('/logout', methods=['POST'])
def logout():
    session.pop(SESSION_KEY, None)
    g._portal_user = None
    flash('Sessao encerrada.', 'info')
    return redirect(url_for('portal_cliente.login'))


# ---------------------------------------------------------------- dashboard
@portal_cliente_bp.route('/')
@portal_required
def dashboard():
    from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService, ETAPAS
    user = _current_portal_user()
    busca = request.args.get('busca', '')
    status_filtro = request.args.get('status', '')
    nfs = CarviaPortalStatusService.listar_nfs(user, busca=busca or None)
    if status_filtro:
        nfs = [n for n in nfs if n['atual_key'] == status_filtro]
    return render_template('carvia/portal/dashboard.html', user=user, nfs=nfs, etapas=ETAPAS,
                           busca=busca, status_filtro=status_filtro)


@portal_cliente_bp.route('/nf/<numero>')
@portal_required
def detalhe_nf(numero):
    from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService
    user = _current_portal_user()
    nf = CarviaPortalStatusService.get_nf_escopada(user, numero)
    if nf is None:
        flash('NF nao encontrada no seu acesso.', 'warning')
        return redirect(url_for('portal_cliente.dashboard'))
    status = CarviaPortalStatusService.status_nf(nf)
    dados = CarviaPortalStatusService.dados_detalhe(nf)
    return render_template('carvia/portal/detalhe_nf.html', user=user, nf=nf, status=status, dados=dados)


@portal_cliente_bp.route('/nf/<numero>/arquivo/<tipo>')
@portal_required
def baixar_arquivo_nf(numero, tipo):
    """Download ESCOPADO de um arquivo da NF (Danfe/DACTE/Fatura/Canhoto). So serve se a NF
    pertencer ao escopo de CNPJs do usuario do portal (seguranca: reusa get_nf_escopada)."""
    from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService
    user = _current_portal_user()
    nf = CarviaPortalStatusService.get_nf_escopada(user, numero)
    if nf is None:
        flash('NF nao encontrada no seu acesso.', 'warning')
        return redirect(url_for('portal_cliente.dashboard'))
    path = CarviaPortalStatusService.arquivo_path(nf, tipo)
    if not path:
        flash('Arquivo nao disponivel para esta NF.', 'warning')
        return redirect(url_for('portal_cliente.detalhe_nf', numero=numero))
    from app.utils.file_storage import get_file_storage
    url = get_file_storage().get_file_url(path)
    if not url:
        flash('Nao foi possivel acessar o arquivo agora.', 'danger')
        return redirect(url_for('portal_cliente.detalhe_nf', numero=numero))
    return redirect(url)


# -------------------------------------------------------------------- cotar
@portal_cliente_bp.route('/cotar', methods=['GET', 'POST'])
@portal_required
def cotar():
    user = _current_portal_user()
    resultado = None
    erro = None
    if request.method == 'POST':
        try:
            from app.carvia.services.pricing.carvia_tabela_service import CarviaTabelaService
            peso = float((request.form.get('peso') or '0').replace(',', '.') or 0)
            valor = float((request.form.get('valor_mercadoria') or '0').replace(',', '.') or 0)
            uf_destino = (request.form.get('uf_destino') or '').strip().upper()
            cidade_destino = (request.form.get('cidade_destino') or '').strip()
            uf_origem = (request.form.get('uf_origem') or 'SP').strip().upper()
            cnpjs = list(user.cnpjs_permitidos())
            cnpj_cliente = cnpjs[0] if cnpjs else None
            resultado = CarviaTabelaService().cotar_carvia(
                peso=peso, valor_mercadoria=valor, uf_origem=uf_origem, uf_destino=uf_destino,
                cidade_destino=cidade_destino, cnpj_cliente=cnpj_cliente)
            if not resultado:
                erro = 'Nenhuma opcao de frete encontrada para esse destino.'
        except Exception as e:
            erro = f'Nao foi possivel cotar: {e}'
    return render_template('carvia/portal/cotar.html', user=user, resultado=resultado, erro=erro)
