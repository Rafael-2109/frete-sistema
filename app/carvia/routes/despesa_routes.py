"""
Rotas de Despesas CarVia — CRUD completo
"""

import logging
from datetime import date, datetime

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.carvia.models import CarviaDespesa

logger = logging.getLogger(__name__)

TIPOS_DESPESA = ['CONTABILIDADE', 'GRIS', 'SEGURO', 'OUTROS', 'DESCONSIDERAR', 'COMISSAO']
STATUS_DESPESA = ['PENDENTE', 'PAGO', 'CANCELADO']


def register_despesa_routes(bp):

    @bp.route('/despesas') # type: ignore
    @login_required
    def listar_despesas(): # type: ignore
        """Lista despesas CarVia com filtros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaDespesa)

        if tipo_filtro:
            query = query.filter(CarviaDespesa.tipo_despesa == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaDespesa.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaDespesa.descricao.ilike(busca_like),
                    CarviaDespesa.observacoes.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'tipo_despesa': CarviaDespesa.tipo_despesa,
            'valor': CarviaDespesa.valor,
            'data_despesa': CarviaDespesa.data_despesa,
            'data_vencimento': CarviaDespesa.data_vencimento,
            'status': CarviaDespesa.status,
            'criado_em': CarviaDespesa.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaDespesa.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        today = date.today()

        return render_template(
            'carvia/despesas/listar.html',
            despesas=paginacao.items,
            paginacao=paginacao,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
            tipos_despesa=TIPOS_DESPESA,
            today=today,
        )

    @bp.route('/despesas/criar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_despesa(): # type: ignore
        """Cria nova despesa"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            tipo_despesa = request.form.get('tipo_despesa', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_despesa_str = request.form.get('data_despesa', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            # Validacoes
            if not tipo_despesa or not valor_str or not data_despesa_str:
                flash('Tipo, valor e data da despesa sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.criar_despesa'))

            if tipo_despesa not in TIPOS_DESPESA:
                flash('Tipo de despesa invalido.', 'warning')
                return redirect(url_for('carvia.criar_despesa'))

            try:
                # Aceitar virgula como separador decimal
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.criar_despesa'))

                data_despesa = date.fromisoformat(data_despesa_str)
                data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None

                despesa = CarviaDespesa(
                    tipo_despesa=tipo_despesa,
                    descricao=descricao or None,
                    valor=valor,
                    data_despesa=data_despesa,
                    data_vencimento=data_vencimento,
                    status='PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(despesa)
                db.session.commit()

                flash(f'Despesa #{despesa.id} criada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa.id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar despesa: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/despesas/criar.html',
            tipos_despesa=TIPOS_DESPESA,
        )

    @bp.route('/despesas/<int:despesa_id>') # type: ignore
    @login_required
    def detalhe_despesa(despesa_id): # type: ignore
        """Detalhe de uma despesa"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        despesa = db.session.get(CarviaDespesa, despesa_id)
        if not despesa:
            flash('Despesa nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_despesas'))

        return render_template(
            'carvia/despesas/detalhe.html',
            despesa=despesa,
        )

    @bp.route('/despesas/<int:despesa_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_despesa(despesa_id): # type: ignore
        """Edita uma despesa existente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        despesa = db.session.get(CarviaDespesa, despesa_id)
        if not despesa:
            flash('Despesa nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_despesas'))

        if despesa.status == 'CANCELADO':
            flash('Nao e possivel editar despesa cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

        if request.method == 'POST':
            tipo_despesa = request.form.get('tipo_despesa', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_despesa_str = request.form.get('data_despesa', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not tipo_despesa or not valor_str or not data_despesa_str:
                flash('Tipo, valor e data da despesa sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.editar_despesa', despesa_id=despesa_id))

            if tipo_despesa not in TIPOS_DESPESA:
                flash('Tipo de despesa invalido.', 'warning')
                return redirect(url_for('carvia.editar_despesa', despesa_id=despesa_id))

            try:
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.editar_despesa', despesa_id=despesa_id))

                despesa.tipo_despesa = tipo_despesa
                despesa.descricao = descricao or None
                despesa.valor = valor
                despesa.data_despesa = date.fromisoformat(data_despesa_str)
                despesa.data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None
                despesa.observacoes = observacoes or None

                db.session.commit()
                flash('Despesa atualizada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar despesa {despesa_id}: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/despesas/editar.html',
            despesa=despesa,
            tipos_despesa=TIPOS_DESPESA,
        )

    @bp.route('/despesas/<int:despesa_id>/status', methods=['POST']) # type: ignore
    @login_required
    def atualizar_status_despesa(despesa_id): # type: ignore
        """Atualiza status de uma despesa"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        despesa = db.session.get(CarviaDespesa, despesa_id)
        if not despesa:
            flash('Despesa nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_despesas'))

        novo_status = request.form.get('status')
        if novo_status not in STATUS_DESPESA:
            flash('Status invalido.', 'warning')
            return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

        try:
            # GAP-06: Se revertendo de PAGO para outro status, remover movimentacao financeira
            if despesa.status == 'PAGO' and novo_status != 'PAGO':
                from app.carvia.routes.fluxo_caixa_routes import _remover_movimentacao
                _remover_movimentacao('despesa', despesa_id)
                despesa.pago_por = None
                despesa.pago_em = None
                logger.info(
                    f"Despesa #{despesa_id}: movimentacao removida ao reverter "
                    f"PAGO -> {novo_status} por {current_user.email}"
                )

            despesa.status = novo_status

            # Ao marcar como PAGO: registrar pago_em/pago_por e criar movimentacao
            if novo_status == 'PAGO':
                data_pagamento_str = request.form.get('data_pagamento', '').strip()
                if not data_pagamento_str:
                    flash('Data de pagamento e obrigatoria para marcar como PAGO.', 'warning')
                    return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))
                try:
                    data_pagamento = date.fromisoformat(data_pagamento_str)
                except ValueError:
                    flash('Data de pagamento invalida.', 'warning')
                    return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))

                despesa.pago_em = datetime.combine(data_pagamento, datetime.min.time())
                despesa.pago_por = current_user.email

                # Criar movimentacao financeira na conta
                from app.carvia.routes.fluxo_caixa_routes import (
                    _criar_movimentacao, _gerar_descricao,
                )
                descricao = _gerar_descricao('despesa', despesa)
                _criar_movimentacao(
                    'despesa', despesa_id,
                    float(despesa.valor or 0), descricao, current_user.email,
                )

            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Movimentacao duplicada despesa #{despesa_id}")
            flash('Este lancamento ja foi processado.', 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar status despesa {despesa_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_despesa', despesa_id=despesa_id))
