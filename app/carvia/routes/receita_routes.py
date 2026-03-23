"""
Rotas de Receitas CarVia — CRUD completo
"""

import logging
from datetime import date, datetime

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.carvia.models import CarviaReceita

logger = logging.getLogger(__name__)

STATUS_RECEITA = ['PENDENTE', 'RECEBIDO', 'CANCELADO']


def register_receita_routes(bp):

    @bp.route('/receitas') # type: ignore
    @login_required
    def listar_receitas(): # type: ignore
        """Lista receitas CarVia com filtros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaReceita)

        if tipo_filtro:
            query = query.filter(CarviaReceita.tipo_receita == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaReceita.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaReceita.descricao.ilike(busca_like),
                    CarviaReceita.observacoes.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'tipo_receita': CarviaReceita.tipo_receita,
            'valor': CarviaReceita.valor,
            'data_receita': CarviaReceita.data_receita,
            'data_vencimento': CarviaReceita.data_vencimento,
            'status': CarviaReceita.status,
            'criado_em': CarviaReceita.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaReceita.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        today = date.today()

        # Tipos existentes para filtro dinamico
        tipos_receita = [
            row[0] for row in
            db.session.query(CarviaReceita.tipo_receita)
            .distinct()
            .order_by(CarviaReceita.tipo_receita)
            .all()
            if row[0]
        ]

        return render_template(
            'carvia/receitas/listar.html',
            receitas=paginacao.items,
            paginacao=paginacao,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
            tipos_receita=tipos_receita,
            today=today,
        )

    @bp.route('/receitas/criar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_receita(): # type: ignore
        """Cria nova receita"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            tipo_receita = request.form.get('tipo_receita', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_receita_str = request.form.get('data_receita', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            # Validacoes
            if not tipo_receita or not valor_str or not data_receita_str:
                flash('Tipo, valor e data da receita sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.criar_receita'))

            try:
                # Aceitar virgula como separador decimal
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.criar_receita'))

                data_receita = date.fromisoformat(data_receita_str)
                data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None

                receita = CarviaReceita(
                    tipo_receita=tipo_receita,
                    descricao=descricao or None,
                    valor=valor,
                    data_receita=data_receita,
                    data_vencimento=data_vencimento,
                    status='PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(receita)
                db.session.commit()

                flash(f'Receita #{receita.id} criada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_receita', receita_id=receita.id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar receita: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template('carvia/receitas/criar.html')

    @bp.route('/receitas/<int:receita_id>') # type: ignore
    @login_required
    def detalhe_receita(receita_id): # type: ignore
        """Detalhe de uma receita"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        receita = db.session.get(CarviaReceita, receita_id)
        if not receita:
            flash('Receita nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_receitas'))

        return render_template(
            'carvia/receitas/detalhe.html',
            receita=receita,
        )

    @bp.route('/receitas/<int:receita_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_receita(receita_id): # type: ignore
        """Edita uma receita existente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        receita = db.session.get(CarviaReceita, receita_id)
        if not receita:
            flash('Receita nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_receitas'))

        if receita.status == 'CANCELADO':
            flash('Nao e possivel editar receita cancelada.', 'warning')
            return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

        if request.method == 'POST':
            tipo_receita = request.form.get('tipo_receita', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_receita_str = request.form.get('data_receita', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not tipo_receita or not valor_str or not data_receita_str:
                flash('Tipo, valor e data da receita sao obrigatorios.', 'warning')
                return redirect(url_for('carvia.editar_receita', receita_id=receita_id))

            try:
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.editar_receita', receita_id=receita_id))

                receita.tipo_receita = tipo_receita
                receita.descricao = descricao or None
                receita.valor = valor
                receita.data_receita = date.fromisoformat(data_receita_str)
                receita.data_vencimento = date.fromisoformat(data_vencimento_str) if data_vencimento_str else None
                receita.observacoes = observacoes or None

                db.session.commit()
                flash('Receita atualizada com sucesso.', 'success')
                return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar receita {receita_id}: {e}")
                flash(f'Erro: {e}', 'danger')

        return render_template(
            'carvia/receitas/editar.html',
            receita=receita,
        )

    @bp.route('/receitas/<int:receita_id>/status', methods=['POST']) # type: ignore
    @login_required
    def atualizar_status_receita(receita_id): # type: ignore
        """Atualiza status de uma receita"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        receita = db.session.get(CarviaReceita, receita_id)
        if not receita:
            flash('Receita nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_receitas'))

        novo_status = request.form.get('status')
        if novo_status not in STATUS_RECEITA:
            flash('Status invalido.', 'warning')
            return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

        try:
            # Se revertendo de RECEBIDO para outro status, remover movimentacao financeira
            if receita.status == 'RECEBIDO' and novo_status != 'RECEBIDO':
                from app.carvia.routes.fluxo_caixa_routes import _remover_movimentacao
                _remover_movimentacao('receita', receita_id)
                receita.recebido_por = None
                receita.recebido_em = None
                logger.info(
                    f"Receita #{receita_id}: movimentacao removida ao reverter "
                    f"RECEBIDO -> {novo_status} por {current_user.email}"
                )

            receita.status = novo_status

            # Ao marcar como RECEBIDO: registrar recebido_em/recebido_por e criar movimentacao
            if novo_status == 'RECEBIDO':
                data_recebimento_str = request.form.get('data_recebimento', '').strip()
                if not data_recebimento_str:
                    flash('Data de recebimento e obrigatoria para marcar como RECEBIDO.', 'warning')
                    return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))
                try:
                    data_recebimento = date.fromisoformat(data_recebimento_str)
                except ValueError:
                    flash('Data de recebimento invalida.', 'warning')
                    return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))

                receita.recebido_em = datetime.combine(data_recebimento, datetime.min.time())
                receita.recebido_por = current_user.email

                # Criar movimentacao financeira na conta
                from app.carvia.routes.fluxo_caixa_routes import (
                    _criar_movimentacao, _gerar_descricao,
                )
                descricao = _gerar_descricao('receita', receita)
                _criar_movimentacao(
                    'receita', receita_id,
                    float(receita.valor or 0), descricao, current_user.email,
                )

            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Movimentacao duplicada receita #{receita_id}")
            flash('Este lancamento ja foi processado.', 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar status receita {receita_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_receita', receita_id=receita_id))
