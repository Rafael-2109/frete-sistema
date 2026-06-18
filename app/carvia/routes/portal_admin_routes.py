"""Gestao INTERNA dos usuarios do Portal do Cliente (stream 5).

Operador CarVia aprova/rejeita/bloqueia e define o escopo (CNPJs ou Cliente Comercial).
Rotas no blueprint carvia (interno, @login_required + sistema_carvia). O portal externo em si
vive em app/carvia/portal_cliente.py (blueprint separado).
"""
import logging

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_portal_admin_routes(bp):

    def _guard():
        return getattr(current_user, 'sistema_carvia', False)

    @bp.route('/portal-usuarios')  # type: ignore
    @login_required
    def listar_portal_usuarios():  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.models.portal import CarviaPortalUsuario, PORTAL_STATUSES, PORTAL_ESCOPOS
        from app.carvia.models.clientes import CarviaCliente
        status_filtro = request.args.get('status', '')
        grupo_filtro = request.args.get('grupo', '')
        busca = request.args.get('busca', '')
        q = CarviaPortalUsuario.query
        if status_filtro:
            q = q.filter(CarviaPortalUsuario.status == status_filtro)
        if grupo_filtro:
            q = q.filter(CarviaPortalUsuario.grupo_empresa.ilike(f'%{grupo_filtro}%'))
        if busca:
            like = f'%{busca}%'
            q = q.filter(db.or_(
                CarviaPortalUsuario.nome.ilike(like),
                CarviaPortalUsuario.email.ilike(like),
                CarviaPortalUsuario.grupo_empresa.ilike(like)))
        usuarios = q.order_by(CarviaPortalUsuario.status, CarviaPortalUsuario.criado_em.desc().nullslast()).all()
        clientes = CarviaCliente.query.filter_by(ativo=True).order_by(CarviaCliente.nome_comercial).all()
        return render_template('carvia/portal_admin/listar.html',
                               usuarios=usuarios, clientes=clientes,
                               statuses=PORTAL_STATUSES, escopos=PORTAL_ESCOPOS,
                               status_filtro=status_filtro, grupo_filtro=grupo_filtro, busca=busca)

    # ---- Acesso INTERNO ao portal (CarVia ve a MESMA tela do cliente, read-only) ----
    def _portal_user_ativo(uid):
        from app.carvia.models.portal import CarviaPortalUsuario
        return db.session.get(CarviaPortalUsuario, uid)

    @bp.route('/portal-usuarios/<int:uid>/ver')  # type: ignore
    @login_required
    def ver_portal(uid):  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService, ETAPAS
        cliente = _portal_user_ativo(uid)
        if cliente is None:
            flash('Usuario do portal nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_portal_usuarios'))
        busca = request.args.get('busca', '')
        status_filtro = request.args.get('status', '')
        nfs = CarviaPortalStatusService.listar_nfs(cliente, busca=busca or None)
        if status_filtro:
            nfs = [n for n in nfs if n['atual_key'] == status_filtro]
        return render_template('carvia/portal/dashboard.html', interno=True, cliente=cliente,
                               nfs=nfs, etapas=ETAPAS, busca=busca, status_filtro=status_filtro)

    @bp.route('/portal-usuarios/<int:uid>/nf/<numero>')  # type: ignore
    @login_required
    def ver_portal_nf(uid, numero):  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService
        cliente = _portal_user_ativo(uid)
        if cliente is None:
            flash('Usuario do portal nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_portal_usuarios'))
        nf = CarviaPortalStatusService.get_nf_escopada(cliente, numero)
        if nf is None:
            flash('NF fora do escopo deste cliente.', 'warning')
            return redirect(url_for('carvia.ver_portal', uid=uid))
        status = CarviaPortalStatusService.status_nf(nf)
        dados = CarviaPortalStatusService.dados_detalhe(nf)
        return render_template('carvia/portal/detalhe_nf.html', interno=True, cliente=cliente,
                               nf=nf, status=status, dados=dados)

    @bp.route('/portal-usuarios/<int:uid>/nf/<numero>/arquivo/<tipo>')  # type: ignore
    @login_required
    def ver_portal_arquivo(uid, numero, tipo):  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService
        cliente = _portal_user_ativo(uid)
        if cliente is None:
            return redirect(url_for('carvia.listar_portal_usuarios'))
        nf = CarviaPortalStatusService.get_nf_escopada(cliente, numero)
        path = CarviaPortalStatusService.arquivo_path(nf, tipo) if nf else None
        if not path:
            flash('Arquivo indisponivel.', 'warning')
            return redirect(url_for('carvia.ver_portal_nf', uid=uid, numero=numero))
        from app.utils.file_storage import get_file_storage
        url = get_file_storage().get_file_url(path)
        return redirect(url) if url else redirect(url_for('carvia.ver_portal_nf', uid=uid, numero=numero))

    @bp.route('/portal-usuarios/<int:uid>/aprovar', methods=['POST'])  # type: ignore
    @login_required
    def aprovar_portal_usuario(uid):  # type: ignore
        return _acao(uid, lambda u, svc: (svc.aprovar(
            u, operador=current_user.email,
            tipo_escopo=request.form.get('tipo_escopo'),
            cnpjs=(request.form.get('cnpjs') or '').replace(';', '\n').replace(',', '\n').split('\n'),
            cliente_comercial_id=request.form.get('cliente_comercial_id', type=int)),
            'Usuario aprovado e escopo definido.'))

    @bp.route('/portal-usuarios/<int:uid>/escopo', methods=['POST'])  # type: ignore
    @login_required
    def escopo_portal_usuario(uid):  # type: ignore
        return _acao(uid, lambda u, svc: (svc.set_escopo(
            u, tipo_escopo=request.form.get('tipo_escopo'),
            cnpjs=(request.form.get('cnpjs') or '').replace(';', '\n').replace(',', '\n').split('\n'),
            cliente_comercial_id=request.form.get('cliente_comercial_id', type=int)),
            'Escopo atualizado.'))

    @bp.route('/portal-usuarios/<int:uid>/rejeitar', methods=['POST'])  # type: ignore
    @login_required
    def rejeitar_portal_usuario(uid):  # type: ignore
        return _acao(uid, lambda u, svc: (svc.rejeitar(u, operador=current_user.email), 'Usuario rejeitado.'))

    @bp.route('/portal-usuarios/<int:uid>/status', methods=['POST'])  # type: ignore
    @login_required
    def status_portal_usuario(uid):  # type: ignore
        novo = request.form.get('status')
        return _acao(uid, lambda u, svc: (svc.definir_status(u, novo), f'Status alterado para {novo}.'))

    def _acao(uid, fn):
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.models.portal import CarviaPortalUsuario
        from app.carvia.services.documentos.portal_auth_service import (
            CarviaPortalAuthService, PortalAuthError)
        u = db.session.get(CarviaPortalUsuario, uid)
        if u is None:
            flash('Usuario nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_portal_usuarios'))
        try:
            res = fn(u, CarviaPortalAuthService)
            msg = res[1] if isinstance(res, tuple) and len(res) > 1 else 'Operacao concluida.'
            db.session.commit()
            flash(msg, 'success')
        except (PortalAuthError, ValueError) as e:
            db.session.rollback(); flash(str(e), 'warning')
        except Exception as e:
            db.session.rollback(); logger.error(f'Erro portal admin {uid}: {e}'); flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.listar_portal_usuarios'))
