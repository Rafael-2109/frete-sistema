"""
Rotas de CTe Subcontrato CarVia — Listagem e detalhe de subcontratos
"""

import logging
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.carvia.models import CarviaSubcontrato, CarviaOperacao

logger = logging.getLogger(__name__)


def register_subcontrato_routes(bp):

    @bp.route('/subcontratos')
    @login_required
    def listar_subcontratos():
        """Lista subcontratos com filtros e paginacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')

        query = db.session.query(CarviaSubcontrato).join(
            CarviaOperacao,
            CarviaSubcontrato.operacao_id == CarviaOperacao.id,
        )

        if status_filtro:
            query = query.filter(CarviaSubcontrato.status == status_filtro)

        if busca:
            busca_like = f'%{busca}%'
            from app.transportadoras.models import Transportadora
            query = query.outerjoin(
                Transportadora,
                CarviaSubcontrato.transportadora_id == Transportadora.id,
            ).filter(
                db.or_(
                    Transportadora.razao_social.ilike(busca_like),
                    Transportadora.cnpj.ilike(busca_like),
                    CarviaSubcontrato.cte_numero.ilike(busca_like),
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                )
            )

        query = query.order_by(CarviaSubcontrato.criado_em.desc())
        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            'carvia/subcontratos/listar.html',
            subcontratos=paginacao.items,
            paginacao=paginacao,
            status_filtro=status_filtro,
            busca=busca,
        )

    @bp.route('/subcontratos/<int:sub_id>')
    @login_required
    def detalhe_subcontrato(sub_id):
        """Detalhe de um subcontrato com cross-links"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            flash('CTe Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_subcontratos'))

        operacao = db.session.get(CarviaOperacao, sub.operacao_id)

        return render_template(
            'carvia/subcontratos/detalhe.html',
            sub=sub,
            operacao=operacao,
        )
