"""Visao OPERACIONAL interna do Portal do Cliente (stream 5).

Diferente de portal_admin_routes (gestao de usuarios externos) e do "ver como cliente"
(/portal-usuarios/<uid>/ver, escopado por 1 cliente), esta visao mostra ao operador CarVia
(sistema_carvia) TODAS as NFs ATIVAS com a MESMA UI do portal (cards + timeline 5 etapas),
filtrando por grupo de cliente, cliente comercial, CNPJ, UF e etapa de rastreamento.

Read-only. Blueprint carvia (interno, @login_required + sistema_carvia). Reusa a resolucao de
CNPJs do portal (grupo -> membros, cliente -> CarviaClienteEndereco) em CarviaPortalStatusService.
"""
import logging

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)


def register_portal_operacional_routes(bp):

    def _guard():
        return getattr(current_user, 'sistema_carvia', False)

    @bp.route('/rastreamento')  # type: ignore
    @login_required
    def rastreamento():  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.services.documentos.portal_status_service import (
            CarviaPortalStatusService, ETAPAS)
        from app.carvia.models.tabelas import CarviaGrupoCliente
        from app.carvia.models.clientes import CarviaCliente

        grupo_id = request.args.get('grupo_id', type=int)
        cliente_id = request.args.get('cliente_id', type=int)
        cnpj = (request.args.get('cnpj', '') or '').strip()
        uf = (request.args.get('uf', '') or '').strip()
        status_filtro = (request.args.get('status', '') or '').strip()

        tem_filtro = any([grupo_id, cliente_id, cnpj, uf, status_filtro])
        nfs = CarviaPortalStatusService.listar_nfs_operacional(
            grupo_id=grupo_id, cliente_id=cliente_id, cnpj=cnpj or None,
            uf=uf or None, status_etapa=status_filtro or None)

        grupos = (CarviaGrupoCliente.query.filter_by(ativo=True)
                  .order_by(CarviaGrupoCliente.nome).all())
        clientes = (CarviaCliente.query.filter_by(ativo=True)
                    .order_by(CarviaCliente.nome_comercial).all())
        ufs = CarviaPortalStatusService.ufs_distintas()
        return render_template(
            'carvia/portal/operacional.html', nfs=nfs, etapas=ETAPAS,
            grupos=grupos, clientes=clientes, ufs=ufs,
            grupo_id=grupo_id, cliente_id=cliente_id, cnpj=cnpj, uf=uf,
            status_filtro=status_filtro, tem_filtro=tem_filtro)

    @bp.route('/rastreamento/nf/<numero>')  # type: ignore
    @login_required
    def rastreamento_nf(numero):  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService
        nf = CarviaPortalStatusService.get_nf(numero)
        if nf is None:
            flash('NF nao encontrada.', 'warning')
            return redirect(url_for('carvia.rastreamento'))
        status = CarviaPortalStatusService.status_nf(nf)
        dados = CarviaPortalStatusService.dados_detalhe(nf)
        return render_template('carvia/portal/detalhe_nf.html', operacional=True,
                               nf=nf, status=status, dados=dados)

    @bp.route('/rastreamento/nf/<numero>/arquivo/<tipo>')  # type: ignore
    @login_required
    def rastreamento_arquivo(numero, tipo):  # type: ignore
        if not _guard():
            flash('Acesso negado.', 'danger'); return redirect(url_for('main.dashboard'))
        from app.carvia.services.documentos.portal_status_service import CarviaPortalStatusService
        nf = CarviaPortalStatusService.get_nf(numero)
        path = CarviaPortalStatusService.arquivo_path(nf, tipo) if nf else None
        if not path:
            flash('Arquivo indisponivel.', 'warning')
            return redirect(url_for('carvia.rastreamento_nf', numero=numero))
        from app.utils.file_storage import get_file_storage
        url = get_file_storage().get_file_url(path)
        return redirect(url) if url else redirect(url_for('carvia.rastreamento_nf', numero=numero))
