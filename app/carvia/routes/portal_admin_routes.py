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
        q = CarviaPortalUsuario.query
        if status_filtro:
            q = q.filter(CarviaPortalUsuario.status == status_filtro)
        usuarios = q.order_by(CarviaPortalUsuario.status, CarviaPortalUsuario.criado_em.desc().nullslast()).all()
        clientes = CarviaCliente.query.filter_by(ativo=True).order_by(CarviaCliente.nome_comercial).all()
        return render_template('carvia/portal_admin/listar.html',
                               usuarios=usuarios, clientes=clientes,
                               statuses=PORTAL_STATUSES, escopos=PORTAL_ESCOPOS, status_filtro=status_filtro)

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
