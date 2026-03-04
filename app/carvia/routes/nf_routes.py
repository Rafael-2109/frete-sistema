"""
Rotas de NF Venda CarVia — Listagem, detalhe e cancelamento de NFs importadas
"""

import logging
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import CarviaNf, CarviaOperacaoNf
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def register_nf_routes(bp):

    @bp.route('/nfs')
    @login_required
    def listar_nfs():
        """Lista NFs importadas com filtros e paginacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        busca = request.args.get('busca', '')
        tipo_filtro = request.args.get('tipo_fonte', '')
        status_filtro = request.args.get('status', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        # Subquery: contar CTes vinculados a cada NF
        subq_ctes = db.session.query(
            CarviaOperacaoNf.nf_id,
            func.count(CarviaOperacaoNf.operacao_id).label('qtd_ctes')
        ).group_by(CarviaOperacaoNf.nf_id).subquery()

        query = db.session.query(
            CarviaNf, subq_ctes.c.qtd_ctes
        ).outerjoin(
            subq_ctes, CarviaNf.id == subq_ctes.c.nf_id
        )

        # Filtro de status: por padrao exclui CANCELADA
        if status_filtro == 'CANCELADA':
            query = query.filter(CarviaNf.status == 'CANCELADA')
        elif status_filtro == 'TODAS':
            pass  # Sem filtro de status
        else:
            # Padrao: apenas ATIVA
            query = query.filter(CarviaNf.status != 'CANCELADA')

        if tipo_filtro:
            query = query.filter(CarviaNf.tipo_fonte == tipo_filtro)

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaNf.numero_nf.ilike(busca_like),
                    CarviaNf.nome_emitente.ilike(busca_like),
                    CarviaNf.cnpj_emitente.ilike(busca_like),
                    CarviaNf.nome_destinatario.ilike(busca_like),
                    CarviaNf.chave_acesso_nf.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'numero_nf': func.lpad(func.coalesce(CarviaNf.numero_nf, ''), 20, '0'),
            'emitente': CarviaNf.nome_emitente,
            'valor_total': CarviaNf.valor_total,
            'peso_bruto': CarviaNf.peso_bruto,
            'data_emissao': CarviaNf.data_emissao,
            'criado_em': CarviaNf.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaNf.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            'carvia/nfs/listar.html',
            nfs=paginacao.items,
            paginacao=paginacao,
            busca=busca,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            sort=sort,
            direction=direction,
        )

    @bp.route('/nfs/<int:nf_id>')
    @login_required
    def detalhe_nf(nf_id):
        """Detalhe de uma NF com itens e cross-link para CTes CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            flash('NF nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        itens = nf.itens.all()

        # Operacoes vinculadas (CTes CarVia) via junction
        operacoes = nf.operacoes.all()

        # Cross-links: subcontratos, faturas cliente, faturas transportadora
        from app.carvia.models import CarviaSubcontrato
        op_ids = [op.id for op in operacoes]
        subcontratos = []
        if op_ids:
            subcontratos = CarviaSubcontrato.query.filter(
                CarviaSubcontrato.operacao_id.in_(op_ids)
            ).all()

        faturas_cliente = nf.get_faturas_cliente()
        faturas_transportadora = nf.get_faturas_transportadora()

        return render_template(
            'carvia/nfs/detalhe.html',
            nf=nf,
            itens=itens,
            operacoes=operacoes,
            subcontratos=subcontratos,
            faturas_cliente=faturas_cliente,
            faturas_transportadora=faturas_transportadora,
        )

    # ==================== CANCELAR NF ====================

    @bp.route('/nfs/<int:nf_id>/cancelar', methods=['POST'])
    @login_required
    def cancelar_nf(nf_id):
        """Cancela uma NF (soft-delete conforme GAP-20)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            flash('NF nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        if nf.status == 'CANCELADA':
            flash('NF ja esta cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

        motivo = request.form.get('motivo_cancelamento', '').strip()
        if not motivo:
            flash('Motivo de cancelamento e obrigatorio.', 'warning')
            return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))

        try:
            nf.status = 'CANCELADA'
            nf.cancelado_em = agora_utc_naive()
            nf.cancelado_por = current_user.email
            nf.motivo_cancelamento = motivo
            db.session.commit()

            logger.info(
                f"NF cancelada: nf_id={nf.id} numero={nf.numero_nf} "
                f"por={current_user.email} motivo={motivo}"
            )
            flash(f'NF {nf.numero_nf} cancelada com sucesso.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cancelar NF {nf_id}: {e}")
            flash(f'Erro ao cancelar NF: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_nf', nf_id=nf_id))
